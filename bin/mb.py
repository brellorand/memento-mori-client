#!/usr/bin/env python

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import cached_property
from pathlib import Path

from cli_command_parser import Command, ParamUsageError, main
from cli_command_parser.parameters import SubCommand, Flag, Counter, Option, Action, ParamGroup
from cli_command_parser.inputs import Path as IPath, NumRange, File as IFile, FileWrapper

from mm.__version__ import __author_email__, __version__  # noqa
from mm.session import MementoMoriSession
from mm.enums import Region, Locale
from mm.fs import path_repr, sanitize_file_name
from mm.mb_models import RANK_BONUS_STATS, WorldGroup, Character as MBCharacter
from mm.output import OUTPUT_FORMATS, YAML, CompactJSONEncoder, pprint
from mm.utils import FutureWaiter

log = logging.getLogger(__name__)

DIR = IPath(type='dir')
IN_FILE = IPath(type='file', exists=True)


class MBDataCLI(Command, description='Memento Mori MB Data Viewer / Downloader', option_name_mode='*-'):
    action = SubCommand()
    no_client_cache = Flag('-C', help='Do not read cached game/catalog data')
    no_mb_cache = Flag('-M', help='Do not read cached MB data')
    config_file = Option(
        '-cf', type=IPath(type='file'), help='Config file path (default: ~/.config/memento-mori-client)'
    )
    locale = Option('-loc', choices=Locale, default='EnUs', help='Locale to use for text resources')
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        from mm.logging import init_logging

        init_logging(self.verbose)

    @cached_property
    def mm_session(self) -> MementoMoriSession:
        return MementoMoriSession(
            self.config_file,
            use_auth_cache=not self.no_client_cache,
            use_data_cache=not self.no_client_cache,
            use_mb_cache=not self.no_mb_cache,
            mb_locale=self.locale,
        )


# region Save Commands


class Save(MBDataCLI, help='Save MB-related data'):
    item = SubCommand()
    output: Path = Option('-o', type=DIR, help='Output directory', required=True)
    force = Flag('-F', help='Force files to be overwritten even if they already exist')


class Catalog(Save, help='Save the MB catalog, which lists MB files and their hashes'):
    def main(self):
        path = self.output.joinpath('mb-catalog.json')
        if not self.force and path.exists():
            log.warning(f'{path_repr(path)} already exists - use --force to overwrite')
        else:
            data = self.mm_session.mb.catalog
            path.parent.mkdir(parents=True, exist_ok=True)
            log.info(f'Saving {path_repr(path)}')
            with path.open('w', encoding='utf-8', newline='\n') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, cls=CompactJSONEncoder)


class Mbs(Save, help='Save the MB files listed in the MB catalog'):
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')
    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of files to download')

    def main(self):
        if file_names := self._get_names():
            self.save_files(file_names)
        else:
            log.info('All MB files have already been downloaded (use --force to force them to be re-downloaded)')

    def save_files(self, file_names: list[str]):
        self.output.mkdir(parents=True, exist_ok=True)
        log.info(f'Downloading {len(file_names):,d} files using {self.parallel} threads')
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.mm_session.mb.get_raw_data, name): name for name in file_names}
            with FutureWaiter(executor)(futures, add_bar=not self.verbose, unit=' files') as waiter:
                for future in waiter:
                    self._save_data(futures[future], future.result())

    def _get_names(self) -> list[str]:
        to_download = list(self.mm_session.mb.file_map)
        if not self.force and self.output.exists():
            to_download = [name for name in to_download if not self.output.joinpath(name + '.json').exists()]

        if self.limit:
            return to_download[: self.limit]
        return to_download

    def _save_data(self, name: str, data):
        out_path = self.output.joinpath(name + '.json')
        log.debug(f'Saving {path_repr(out_path)}')
        with out_path.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, cls=CompactJSONEncoder, max_line_len=119)


class RawData(Save, help='Download files listed in the DownloadRawDataMB list'):
    with ParamGroup('File', mutually_exclusive=True, required=True):
        name = Option(
            '-n', metavar='FilePath', nargs='+', help='One or more relative FilePath values from DownloadRawDataMB'
        )
        pattern = Option(
            '-p', metavar='GLOB', help='Download files listed in DownloadRawDataMB that match this glob pattern'
        )
        all = Flag('-a', help='Download all files listed in DownloadRawDataMB')

    skip_validation = Flag('-V', help='Skip path validation against DownloadRawDataMB entries (only applies to --name)')
    parallel: int = Option('-P', type=NumRange(min=1), default=4, help='Number of download threads to use in parallel')
    limit: int = Option('-L', type=NumRange(min=1), help='Limit the number of files to download')
    dry_run = Flag('-D', help='Print the names of the files that would be downloaded instead of downloading them')

    def main(self):
        if paths := self._get_paths():
            self.save_files(paths)
        else:
            log.info('All files have already been downloaded (use --force to force them to be re-downloaded)')

    def save_files(self, paths: list[str]):
        prefix = '[DRY RUN] Would download' if self.dry_run else 'Downloading'
        log.info(f'{prefix} {len(paths):,d} files using {self.parallel} threads')
        if self.dry_run:
            log.info('Files that would be downloaded:')
            for path in sorted(paths):
                print(f' - {path}')
        else:
            self._download(paths)

    def _download(self, paths: list[str]):
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {executor.submit(self.mm_session.data_client.get_raw_data, path): path for path in paths}
            with FutureWaiter(executor)(futures, add_bar=not self.verbose, unit=' files') as waiter:
                for future in waiter:
                    self._save(futures[future], future.result())

    @cached_property
    def raw_data_info(self) -> list[dict[str, int | str | bool]]:
        return self.mm_session.mb.get_raw_data('DownloadRawDataMB')

    def _get_paths(self) -> list[str]:
        if self.pattern:
            from fnmatch import filter

            to_download = filter((row['FilePath'] for row in self.raw_data_info), self.pattern)
        elif self.name:
            if self.skip_validation:
                to_download = self.name
            else:
                names = set(self.name)
                to_download = {row['FilePath'] for row in self.raw_data_info}.intersection(names)
                if bad := names.difference(to_download):
                    bad_str = ', '.join(sorted(bad))
                    raise ParamUsageError(
                        self.__class__.name,
                        f'Invalid values - they do not match FilePath values specified in DownloadRawDataMB: {bad_str}',
                    )
                to_download = sorted(to_download)
        else:  # --all
            to_download = [row['FilePath'] for row in self.raw_data_info]

        if not self.force and self.output.exists():
            to_download = [path for path in to_download if not self.output.joinpath(path).exists()]

        if self.limit:
            return to_download[: self.limit]
        return to_download

    def _save(self, name: str, data: bytes, log_lvl: int = logging.DEBUG):
        path = self.output.joinpath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.log(log_lvl, f'Saving {path_repr(path)}')
        path.write_bytes(data)


class Lyrics(Save, help='Save lament lyrics'):
    no_translation = Flag('-T', help='Do not include the English version of character/lament names')
    english = Flag('-e', help='Use the US version of profile strings instead of localized versions')

    def main(self):
        self.output.mkdir(parents=True, exist_ok=True)
        for char in self.mm_session.mb.characters.values():
            lyrics = char.profile.lament_lyrics_text_en if self.english else char.profile.lament_lyrics_text
            path = self.output.joinpath(sanitize_file_name(self._get_name(char)))
            log.info(f'Saving {path.as_posix()}')
            path.write_text(lyrics, encoding='utf-8')

    def _get_name(self, char: MBCharacter):
        if self.english:
            return f'{char.full_id} {char.full_name_en} - {char.profile.lament_name_en}.txt'
        elif self.no_translation:
            return f'{char.full_id} {char.full_name} - {char.profile.lament_name}.txt'
        else:
            return f'{char.full_id} {char.full_name_with_translation} - {char.profile.lament_name_with_translation}.txt'


# endregion


# region Show Commands


class Show(MBDataCLI, help='Show info from MB files'):
    item = SubCommand()
    format = Option(
        '-f', choices=OUTPUT_FORMATS, default='json-pretty' if YAML is None else 'yaml', help='Output format'
    )

    def pprint(self, data):
        if data:
            pprint(self.format, data)
        else:
            print('No results')


class WorldGroups(Show, help='Show Grand Battle / Legend League world groups'):
    region = Option('-r', type=Region, default=Region.NORTH_AMERICA, help='Filter output to the specified region')
    past = Flag('-p', help='Include past Grand Battle dates (default: only current/future dates)')

    def main(self):
        self.pprint(self.get_groups())

    def get_groups(self):
        groups = []
        for i, group in enumerate(self.mm_session.mb.world_groups):
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

        game_data = self.mm_session.auth_client.game_data
        return {
            'id': group.id,
            'region': group.region.name,
            'worlds': ', '.join(map(str, sorted(game_data.get_world(wid).number for wid in group.world_ids))),
            'grand_battles': [f'{start.isoformat(" ")} ~ {end.isoformat(" ")}' for start, end in grand_battles],
        }


class VIP(Show, choice='vip', help='Show daily VIP rewards by level'):
    item = Action()

    @item(help='Show the daily rewards unlocked at each VIP level')
    def daily_rewards(self):
        data = {
            f'Level {level.level}': [f'{ic.item.display_name} x {ic.count:,d}' for ic in level.daily_rewards]
            for level in self.mm_session.mb.vip_levels
        }
        self.pprint(data)


class Rank(Show, help='Show player rank info'):
    item = Action()
    stat = Option('-s', nargs='+', choices=RANK_BONUS_STATS, help='Filter output to the specified stats (default: all)')
    not_stat = Option('-S', nargs='+', choices=RANK_BONUS_STATS, help='Filter out the specified stats')

    @item(help='Show the ranks at which additional level link slots are unlocked')
    def link_slots(self):
        last = 0
        for num, rank in self.mm_session.mb.player_ranks.items():
            if rank.level_link_slots > last:
                print(f'Rank {num:>3d}: {rank.level_link_slots:>2d} link slots')
                last = rank.level_link_slots

    @item(help='Show the stat bonuses unlocked at each rank')
    def bonuses(self):
        stats = set(self.stat or RANK_BONUS_STATS).difference(self.not_stat)
        output = {}
        last = {}
        for num, rank in self.mm_session.mb.player_ranks.items():
            rank_stats = {k: v for k, v in rank.get_stat_bonuses().items() if k in stats and v and v != last.get(k)}
            if rank_stats:
                last |= rank_stats  # Update instead of replace so filtered out same values will be retained
                output[f'Rank {num}'] = {
                    k: f'{v}%' if '%' in k else f'{v:,d}' if v > 999 else v for k, v in rank_stats.items()
                }

        self.pprint(output)


class Character(Show, choices=('character', 'char'), help='Show character info'):
    item = Action()
    descending = Flag('-d', help='[speed only] Sort output in descending order (default: ascending)')
    show_laments = Flag('-L', help='[summary only] Show lament names')

    @item(help='Show the name of each character with its ID')
    def names(self):
        for num, char in self.mm_session.mb.characters.items():
            print(f'{char.full_id}: {char.full_name}')

    @item(help='Show a basic, high-level character info summary')
    def summary(self):
        chars = self.mm_session.mb.characters.values()
        if self.format == 'json-lines':
            data = [{char.full_id: char.get_summary(show_lament=self.show_laments)} for char in chars]
        else:
            data = {char.full_id: char.get_summary(show_lament=self.show_laments) for char in chars}

        self.pprint(data)

    @item(help='Show a sorted list of characters and their base speeds')
    def speed(self):
        speeds = ((char.speed, char.full_name) for char in self.mm_session.mb.characters.values())
        for speed, name in sorted(speeds, reverse=self.descending):
            print(f'{speed:,d}  {name}')


class ShowCatalog(Show, choice='catalog', help='Show the MB catalog (for debugging purposes)'):
    def main(self):
        self.pprint(self.mm_session.mb.catalog)


# endregion


class GenerateErrorMap(MBDataCLI, help='Generate a mapping of error codes to their error messages'):
    output: FileWrapper = Option(
        '-o',
        type=IFile('w', type='file', allow_dash=True, exists=False, encoding='utf-8'),
        default='-',
        help='Output file',
    )

    def main(self):
        code_message_map = {}
        for key, text in self.mm_session.mb.text_resource_map.items():
            if key.startswith('[ErrorMessage'):
                code = int(key[13:-1])
                code_message_map[code] = text

        with self.output as f:
            f.write('{\n')
            for code, text in code_message_map.items():
                f.write(f'    {code:_d}: {text!r},\n')
            f.write('}\n')


if __name__ == '__main__':
    main()
