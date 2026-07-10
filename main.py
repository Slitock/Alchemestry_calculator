from core.ingredient import Ingredient 
from core.mixed import Mixed 

TEST_INPUT = [
        Ingredient(name = "Черная роза", omnisention = 60, properties = ["А", "А", "В"])
        Ingredient(name = "leg", omnisention = 500, properties = ["Б", "В", "Плюс хит"])
        ]



def main():
    cauldron = []

    print("=== Алхимический калькулятор ===")

    while True:
        print("\nДоступные ингридиенты:")
        for index, ing in enumerate(TEST_INPUT):
            print(f"[{index}] {ing.name}\n    Омнисеция: {ing.omnisention}\n    Эффекты: {ing.properties}")

        if cauldron:
            print(f"\nСейчас в котле: {[ing.name for ing in cauldron]}")
        else:
            print("\nВ котле пока пусто.")

        print("-" * 40)
        print("Команды: [номер] — добавить траву, 'b' — сварить, 'c' — очистить котел, 'q' — выход")
        choice = input("Введите команду: ").strip().lower()

        if choice == 'q':
            print("Закрытие лаборатории...")
            break

        elif choice == 'c':
            cauldron.clear()
            print("Котел полностью очищен!")

        elif choice == 'b':
            if not cauldron:
                print("Котел пуст! Не из чего варить.")
                continue
            
            print("\n=== Начинается процесс варки... ===")

            poison = Mixed(cauldron)

            print("\nФинальный состав зелья (Рецепт):")
            for item in potion.recept:
                print(f" - {item}")
                
            print(f"\nИтоговая омнисенция получившегося зелья: {potion.omnisention}")
            print(f"Итоговые эффекты: {potion.properties}")
            
            # Очищаем котел для следующей варки
            cauldron.clear()
            input("\nНажмите Enter, чтобы продолжить...")

        else:
            # Если ввели число — пытаемся добавить ингредиент по индексу
            try:
                idx = int(choice)
                if 0 <= idx < len(AVAILABLE_INGREDIENTS):
                    selected_ing = AVAILABLE_INGREDIENTS[idx]
                    cauldron.append(selected_ing)
                    print(f"Добавлено: {selected_ing.name}")
                else:
                    print("Нет ингредиента с таким номером!")
            except ValueError:
                print("Неизвестная команда!")

if __name__ == "__main__":
    main()
