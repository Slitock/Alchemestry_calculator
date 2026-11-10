from database.test_bd import PROPERTIES
from database.omnisention_info import OMNISENTION_GRADUET
from math import ceil


class Mixed:
    def __init__(self, ingredients: list, antagonists: dict | None = None):
        # пары антагонистов: из базы (веб) или из database/test_bd.py (консоль)
        self.__antagonists = PROPERTIES if antagonists is None else antagonists

        raw_properties = []
        for ing in ingredients:
            raw_properties += ing.properties

        self.__removed_conflicts = []
        self.__properties = self._resoulve_conflict(raw_properties)

        self.__recept = [ing.name for ing in ingredients]

        self.__crystals = []
        self.__raw_omnisention = sum([ing.omnisention for ing in ingredients])
        self.__omnisention = self._omnisention_counter(
            self.__raw_omnisention, self.__properties
        )

    def _resoulve_conflict(  # обработка эффектов в соответсвии с таблицей.
        self, raw_properties
    ):
        for effect, antieffect in self.__antagonists.items():
            while (effect in raw_properties) and (antieffect in raw_properties):
                raw_properties.remove(effect)
                raw_properties.remove(antieffect)
                self.__removed_conflicts.append((effect, antieffect))

        return raw_properties

    def _omnisention_counter(self, raw_omnisention, properties):  # подсчет омнисенции
        count_of_properties = len(properties)
        range_list = OMNISENTION_GRADUET.get(count_of_properties)

        if range_list == 0:
            return 0
        elif range_list is None:
            min_omn, max_omn = next(reversed(OMNISENTION_GRADUET.values()))
        else:
            min_omn, max_omn = range_list

        added_ihor_cristal = max(0, ceil((min_omn - raw_omnisention) / 5))
        added_cenom_cristal = max(0, ceil((raw_omnisention - max_omn) / 5))

        raw_omnisention = (
            raw_omnisention + 5 * added_ihor_cristal - 5 * added_cenom_cristal
        )

        if added_ihor_cristal > 0:
            self.__recept.append(f"кристал ихора ({added_ihor_cristal} шт.)")
            self.__crystals.append({"type": "ихор", "count": added_ihor_cristal})

        elif added_cenom_cristal > 0:
            self.__recept.append(f"кристал кенома ({added_cenom_cristal} шт.)")
            self.__crystals.append({"type": "кеном", "count": added_cenom_cristal})
        return raw_omnisention

    @property
    def recept(self):
        return self.__recept

    @property
    def raw_omnisention(self):
        return int(self.__raw_omnisention)

    @property
    def crystals(self):
        return [dict(crystal) for crystal in self.__crystals]

    @property
    def removed_conflicts(self):
        return list(self.__removed_conflicts)

    @property
    def properties(self):
        return self.__properties

    @property
    def omnisention(self):
        return self.__omnisention
