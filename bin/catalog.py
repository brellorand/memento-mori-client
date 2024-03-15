#!/usr/bin/env python

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from hashlib import md5
from pathlib import Path

import msgpack
from cli_command_parser import Command, Positional, SubCommand, Flag, Counter, Option, main
from cli_command_parser.inputs import Path as IPath, NumRange

from mm.__version__ import __author_email__, __version__  # noqa
from mm.fs import path_repr
from mm.http_client import AuthClient, DataClient
from mm.output import CompactJSONEncoder
from mm.utils import FutureWaiter

log = logging.getLogger(__name__)

DIR = IPath(type='dir')


class CatalogCLI(Command, description='Memento Mori Catalog Manager', option_name_mode='*-'):
    action = SubCommand()
    no_cache = Flag('-C', help='Do not read cached game/catalog data')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def auth_client(self) -> AuthClient:
        return AuthClient(use_cache=not self.no_cache)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(auth_client=self.auth_client, use_cache=not self.no_cache)


class Show(CatalogCLI, help='Show info'):
    item = Positional(choices=('game_data', 'uri_formats'), help='The item to show')
    sort_keys = Flag('-s', help='Sort keys in dictionaries during serialization')

    def main(self):
        if self.item == 'game_data':
            self.print(self.auth_client.game_data.data)
        elif self.item == 'uri_formats':
            self.print(self.auth_client.game_data.uri_formats)

    def print(self, data):
        print(json.dumps(data, indent=4, sort_keys=self.sort_keys, ensure_ascii=False, cls=CompactJSONEncoder))


# region Save Commands


class Save(CatalogCLI, help='Save catalog metadata to a file'):
    _choices = {'mb': 'The MB catalog', 'assets': 'The full asset catalog'}
    item = SubCommand(title='Items', local_choices=_choices, help='The type of catalog/item to save')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    split = Flag('-s', help='Split the specified catalog into separate files for each top-level key')

    def main(self):
        for name_parts, data, raw in self.iter_names_and_data():
            self._save(data, *name_parts, raw=raw)

    def iter_names_and_data(self):
        name = f'{self.item}-catalog'
        catalog = self.client.asset_catalog if self.item == 'assets' else self.client.mb_catalog
        if self.split:
            for key, val in catalog.data.items():
                yield (name, f'{key}.json'), val, False
        else:
            yield (f'{name}.json',), catalog.data, False

    def _save(self, data, *name, raw: bool = False):
        path = self.output.joinpath(*name)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info(f'Saving {path_repr(path)}')
        if raw:
            path.write_bytes(data)
        else:
            with path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, cls=CompactJSONEncoder)


class AssetData(Save, help='Decoded content from the asset catalog that was base64 encoded'):
    def iter_names_and_data(self):
        asset_catalog = self.client.asset_catalog
        for attr in ('key_data', 'bucket_data', 'entry_data', 'extra_data'):
            yield (f'{attr}.dat',), getattr(asset_catalog, attr), True


class MBContent(Save, choice='mb_content', help='Download all files listed in the MB catalog'):
    force = Flag('-F', help='Force files to be re-downloaded even if they already exist and their hash matches')
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')
    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of files to download')

    def main(self):
        self.output.mkdir(parents=True, exist_ok=True)
        file_names = self._get_names()
        if not file_names:
            log.info('All files have already been downloaded (use --force to force them to be re-downloaded)')
            return

        log.info(f'Downloading {len(file_names):,d} files using {self.parallel} threads')
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.client.get_mb_data, name): name for name in file_names}  # noqa
            with FutureWaiter(executor)(futures, add_bar=not self.verbose, unit=' files') as waiter:
                for future in waiter:
                    self._save_data(futures[future], future.result())

    def _get_names(self) -> list[str]:
        if self.force:
            to_download = list(self.client.mb_catalog.file_map)
        else:
            to_download = []
            for name, info in self.client.mb_catalog.file_map.items():
                if file_hash := self._get_hash(name):
                    if file_hash == info.hash:
                        log.debug(f'Skipping {name} - its hash matches: {file_hash}')
                    else:
                        log.debug(f'File {name} changed - hash={file_hash} expected={info.hash}')
                        # TODO: Save/rename old version?
                        to_download.append(name)
                else:  # The file doesn't already exist or was corrupt
                    to_download.append(name)

        if self.limit:
            return to_download[:self.limit]
        return to_download

    def _get_hash(self, name: str) -> str | None:
        path = self.output.joinpath(name + '.json')
        # TODO: Fix handling for files whose content changes (likely due to fuzzy type handling by CompactJSONEncoder)
        #  examples: LimitedMissionMB, GuildRaidBossMB, GachaCaseUiMB, FriendCampaignMB, CharacterLiveModeMB
        try:
            with path.open('r', encoding='utf-8') as f:
                data = msgpack.packb(json.load(f))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:  # Possibly caused by interrupting the program while saving
            log.debug(f'Will re-download {path_repr(path)} - error during decoding: {e}')
            return None

        return md5(data, usedforsecurity=False).hexdigest()

    def _save_data(self, name: str, data: bytes):
        out_path = self.output.joinpath(name + '.json')
        log.debug(f'Saving {path_repr(out_path)}')
        with out_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, cls=CompactJSONEncoder, max_line_len=119)


# endregion


if __name__ == '__main__':
    main()
