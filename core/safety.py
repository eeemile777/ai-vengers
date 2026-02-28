from typing import Any


def _normalize(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if isinstance(value, str) and value.strip()}


def _extract_ingredient_names(recipe: dict[str, Any]) -> set[str]:
    raw_ingredients = (
        recipe.get("ingredients")
        or recipe.get("required_ingredients")
        or recipe.get("recipe_ingredients")
        or []
    )

    ingredient_names: set[str] = set()
    if isinstance(raw_ingredients, list):
        for item in raw_ingredients:
            if isinstance(item, str):
                name = item.strip().lower()
                if name:
                    ingredient_names.add(name)
                continue

            if isinstance(item, dict):
                maybe_name = (
                    item.get("name")
                    or item.get("ingredient")
                    or item.get("ingredient_name")
                    or item.get("item")
                )
                if isinstance(maybe_name, str) and maybe_name.strip():
                    ingredient_names.add(maybe_name.strip().lower())

    return ingredient_names


def is_safe_to_cook(
    client_intolerances: list[str],
    dish_name: str,
    recipes_cache: list[dict],
) -> bool:
    normalized_dish = dish_name.strip().lower()
    if not normalized_dish:
        return False

    intolerances = _normalize(client_intolerances)

    for recipe in recipes_cache:
        recipe_name = (
            recipe.get("name")
            or recipe.get("dish_name")
            or recipe.get("title")
            or ""
        )
        if not isinstance(recipe_name, str):
            continue
        if recipe_name.strip().lower() != normalized_dish:
            continue

        required_ingredients = _extract_ingredient_names(recipe)
        return len(required_ingredients.intersection(intolerances)) == 0

    return False