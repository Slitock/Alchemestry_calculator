class Potion:
    def __init__(self, recept: list, proerties: list, name: str = None):
        self.__recept = recept
        self.__prorperties = proerties

        if name is None:
            self.__name = ", ".join(proerties)
        else:
            self.__name = name

    def __str__(self):
        recept_str = ", ".join(self.__recept) if self.__recept else "Нет ингредиентов"
        effects_str = (
            ", ".join(self.__prorperties) if self.__prorperties else "Отсутствуют"
        )

        return f"Состав: {recept_str}\n" f"Эффекты: {effects_str}"
