#!/usr/bin/env python

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, Positional, SubCommand, Flag, Counter, Option, main
from cli_command_parser.inputs import Path as IPath, NumRange

from mm.__version__ import __author_email__, __version__  # noqa
from mm.client import DataClient
from mm.data import WorldGroup
from mm.enums import Region
from mm.fs import path_repr
from mm.utils import CompactJSONEncoder, FutureWaiter

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
IN_FILE = IPath(type='file', exists=True)


class MBDataCLI(Command, description='Memento Mori MB Data Viewer / Downloader', option_name_mode='*-'):
    action = SubCommand()
    no_client_cache = Flag('-C', help='Do not read cached game/catalog data')
    no_mb_cache = Flag('-M', help='Do not read cached MB data')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def client(self) -> DataClient:
        return DataClient(use_cache=not self.no_client_cache)

    def _get_mb(self, name: str, json_path: Path | None = None):
        if json_path:
            return json.loads(json_path.read_text('utf-8'))
        return self.client.get_mb_data(name, use_cached=not self.no_mb_cache)

# region Save Commands


class Save(MBDataCLI, help='Save data referenced by a MB file'):
    item = SubCommand()
    metadata: Path = Option('-m', type=IN_FILE, help='JSON file containing downloadable file metadata')
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    force = Flag('-F', help='Force files to be re-downloaded even if they already exist')

    @cached_property
    def raw_data_info(self) -> list[dict[str, int | str | bool]]:
        return self._get_mb('DownloadRawDataMB', self.metadata)

    def _save(self, name: str, data: bytes, log_lvl: int = logging.DEBUG):
        path = self.output.joinpath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.log(log_lvl, f'Saving {path_repr(path)}')
        path.write_bytes(data)


class File(Save, help='Download and save a single file'):
    name = Positional(help='The relative FilePath from DownloadRawDataMB')
    skip_validation = Flag('-V', help='Skip path validation against DownloadRawDataMB entries')

    def main(self):
        if not self.force and self.output.joinpath(self.name).exists():
            raise RuntimeError(f'{self.name} already exists - use --force to download anyways')
        elif not self.skip_validation and not any(row['FilePath'] == self.name for row in self.raw_data_info):
            raise ValueError(f'Invalid file={self.name!r} - does not match any DownloadRawDataMB FilePath')

        self._save(self.name, self.client.get_raw_data(self.name), log_lvl=logging.INFO)


class All(Save, help='Download all files listed in the DownloadRawDataMB list'):
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')
    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of files to download')

    def main(self):
        paths = self._get_paths()
        if not paths:
            log.info('All files have already been downloaded (use --force to force them to be re-downloaded)')
            return

        log.info(f'Downloading {len(paths):,d} files using {self.parallel} threads')
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.client.get_raw_data, path): path for path in paths}
            with FutureWaiter(executor)(futures, add_bar=not self.verbose, unit=' files') as waiter:
                for future in waiter:
                    self._save(futures[future], future.result())

    def _get_paths(self) -> list[str]:
        rows = self.raw_data_info
        if self.force:
            to_download = [row['FilePath'] for row in rows]
        else:
            to_download = [row['FilePath'] for row in rows if not self.output.joinpath(row['FilePath']).exists()]
        if self.limit:
            return to_download[:self.limit]
        return to_download


# endregion


class Show(MBDataCLI, help='Show info from MB files'):
    item = SubCommand()


class WorldGroups(Show, help='Show Grand Battle / Legend League world groups'):
    mb_path: Path = Option('-m', type=IN_FILE, help='JSON file containing WorldGroupMB data (default: download latest)')
    region = Option('-r', type=Region, default=Region.NORTH_AMERICA, help='Filter output to the specified region')
    past = Flag('-p', help='Include past Grand Battle dates (default: only current/future dates)')

    def main(self):
        groups = self.get_groups()
        print(json.dumps(groups, indent=4, ensure_ascii=False, cls=CompactJSONEncoder))

    def get_groups(self):
        groups = []
        for i, group in enumerate(map(WorldGroup, self._get_mb('WorldGroupMB', self.mb_path))):
            if self.region and group.region != self.region:
                log.debug(f'Skipping row {i} with region={group.region}')
                continue

            groups.append(self._get_group_data(group))
        return groups

    def _get_group_data(self, group: WorldGroup):
        if self.past:
            grand_battles = group.grand_battles
        else:
            now = datetime.now()
            grand_battles = [(start, end) for start, end in group.grand_battles if end > now]

        game_data = self.client.game_data
        return {
            'id': group.id,
            'region': group.region.name,
            'worlds': ', '.join(map(str, sorted(game_data.get_world(wid).number for wid in group.world_ids))),
            'grand_battles': [f'{start.isoformat(" ")} ~ {end.isoformat(" ")}' for start, end in grand_battles],
        }


if __name__ == '__main__':
    main()
