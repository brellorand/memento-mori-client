"""
Classes that wrap API responses
"""

from __future__ import annotations

import re
import logging
from functools import cached_property
from typing import Any

from mm.enums import Element, Job, CharacterRarity, Locale, CharacterType, ItemRarityFlags
from mm.properties import DataProperty
from .base import MBEntity, NamedEntity
from .utils import LocalizedString

__all__ = ['Character', 'CharacterProfile']
log = logging.getLogger(__name__)


class Character(NamedEntity, file_name_fmt='CharacterMB'):
    """
    Example:
        "Id": 43,
        "IsIgnore": null,
        "Memo": "【雷啼の魔女】ケルベロス",
        "ActiveSkillIds": [43001, 43002],
        "BaseParameterCoefficient": {"Energy": 83, "Health": 69, "Intelligence": 86, "Muscle": 100},
        "BaseParameterGrossCoefficient": 338,
        "CharacterType": 1,
        "ElementType": 5,
        "InitialBattleParameter": {
            "AttackPower": 0, "Avoidance": 0, "Critical": 0, "CriticalDamageEnhance": 0, "CriticalResist": 0,
            "DamageEnhance": 0, "DamageReflect": 0, "DebuffHit": 0, "DebuffResist": 0, "Defense": 10,
            "DefensePenetration": 0, "Hit": 0, "HP": 0, "HpDrain": 0, "MagicCriticalDamageRelax": 0,
            "MagicDamageRelax": 0, "PhysicalCriticalDamageRelax": 0, "PhysicalDamageRelax": 0, "Speed": 3363
        },
        "ItemRarityFlags": 64,
        "JobFlags": 1,
        "Name2Key": "[CharacterSubName43]",
        "NameKey": "[CharacterName43]",
        "NormalSkillId": 101,
        "PassiveSkillIds": [43003, 43004],
        "RarityFlags": 8,
        "RequireFragmentCount": 60,
        "EndTimeFixJST": "2100-12-31 23:59:59",
        "StartTimeFixJST": "2023-01-17 15:00:00"
    """

    sub_name: str | None = LocalizedString('Name2Key', None)
    name_en: str | None = LocalizedString('NameKey', locale=Locale.EnUs)
    sub_name_en: str | None = LocalizedString('Name2Key', None, locale=Locale.EnUs)

    char_type: CharacterType = DataProperty('CharacterType', CharacterType)
    element: Element = DataProperty('ElementType', Element)

    job: Job = DataProperty('JobFlags', Job)
    rarity: CharacterRarity = DataProperty('RarityFlags', CharacterRarity)
    item_rarity_flags: ItemRarityFlags = DataProperty('ItemRarityFlags', ItemRarityFlags)

    normal_skill_id: int = DataProperty('NormalSkillId')
    active_skill_ids: list[int] = DataProperty('ActiveSkillIds')
    passive_skill_ids: list[int] = DataProperty('PassiveSkillIds')

    speed: int = DataProperty('InitialBattleParameter.Speed')

    def __repr__(self) -> str:
        name, element, job = self.full_name, self.element.name.title(), self.job.name.title()
        return f'<{self.__class__.__name__}[id={self.full_id!r}, {name=}, {element=}, {job=}]>'

    @cached_property
    def full_id(self) -> str:
        return f'CHR_{self.id:06d}'

    @cached_property
    def full_name(self) -> str:
        return f'{self.name} ({self.sub_name})' if self.sub_name else self.name

    @cached_property
    def full_name_en(self) -> str:
        return f'{self.name_en} ({self.sub_name_en})' if self.sub_name_en else self.name_en

    @cached_property
    def full_name_with_translation(self) -> str:
        if self.full_name != self.full_name_en:
            return f'{self.full_name_en} ({self.full_name})'
        return self.full_name

    @cached_property
    def profile(self) -> CharacterProfile:
        return self.mb.character_profiles[self.id]

    def get_summary(self, *, show_lament: bool = False) -> dict[str, Any]:
        summary = {
            'id': self.full_id,
            'name': self.full_name,
            'type': self.char_type.name,
            'element': self.element.name.title(),
            'job': self.job.name.title(),
            'rarity': self.rarity.name,
            # 'item_rarity': self.item_rarity_flags,
        }
        if show_lament:
            summary['lament_title'] = self.profile.lament_name
            summary['lament_title_en'] = self.profile.lament_name_en

        return summary


class CharacterProfile(MBEntity, file_name_fmt='CharacterProfileMB'):
    _size_pat = re.compile(r'^<size=\d+>.*?</size>')
    # fmt: off
    lament_name: str = LocalizedString('LamentJPKey')               # This char's lament name, in the current locale
    lament_lyrics_html: str = LocalizedString('LyricsJPKey')        # This char's lament lyrics, in the current locale
    lament_name_en: str = LocalizedString('LamentUSKey')            # This char's lament name, in English
    lament_lyrics_html_en: str = LocalizedString('LyricsUSKey')     # This char's lament lyrics, in English
    # fmt: on

    @cached_property
    def character(self) -> Character:
        return self.mb.characters[self.id]

    @cached_property
    def lament_name_with_translation(self) -> str:
        if self.lament_name != self.lament_name_en:
            return f'{self.lament_name_en} ({self.lament_name})'
        return self.lament_name

    @cached_property
    def lament_lyrics_text(self) -> str:
        html = self._size_pat.sub('', self.lament_lyrics_html)  # Remove the title from the beginning of the string
        return html.replace('<br>', '\n').strip()

    @cached_property
    def lament_lyrics_text_en(self) -> str:
        html = self._size_pat.sub('', self.lament_lyrics_html_en)  # Remove the title from the beginning of the string
        return html.replace('<br>', '\n').strip()
