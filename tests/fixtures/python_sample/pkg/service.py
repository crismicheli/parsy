from pkg.models import Dog as Canine


def make_sound() -> str:
    dog = Canine()
    return dog.speak()

