import random
from concurrent.futures import ThreadPoolExecutor
from typing import List

from mimesis import Person, Address, Locale, Gender
from mimesis.builtins import RussiaSpecProvider

person = Person(Locale.RU)
address = Address(Locale.RU)
provider = RussiaSpecProvider()


def generate_building() -> str:
    """Генерирует номер здания в разных форматах."""
    options = [
        lambda: str(random.randint(1, 200)),
        lambda: f"{random.randint(1, 100)}/{random.randint(1, 10)}",
        lambda: f"{random.randint(1, 100)}{random.choice('АБВГК')}",
        lambda: f"{random.randint(1, 100)} к.{random.randint(1, 5)}",
    ]
    return random.choice(options)()


def generate_entry() -> dict:
    """Генерирует одну запись."""
    gender = random.choice([Gender.MALE, Gender.FEMALE])
    name, surname = person.full_name(gender).split(" ")[:2]
    return {
        "name": name,
        "surname": surname,
        "patronymic": provider.patronymic(gender),
        "street": address.street_name(),
        "building": generate_building(),
        "apartment": random.randint(1, 1000),
        "phone": int(person.telephone(mask='7##########')),
    }


def generate_entries(count: int) -> List[dict]:
    """Генерирует указанное количество записей."""
    with ThreadPoolExecutor() as executor:
        entries = list(executor.map(lambda _: generate_entry(), range(count)))
    return entries
