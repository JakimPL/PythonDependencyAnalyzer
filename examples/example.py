from typing import Any


class Item:
    def __init__(self, value: Any) -> None:
        self.value = value

    def get_value(self) -> Any:
        return self.value


def inside(x: Any, y: Any) -> Any:
    a = other(y)
    return x + y + a


def other(x: Any) -> Any:
    item = Item(x)
    return item.get_value()


def function(x: Any) -> Any:
    return inside(x, x)


class A:
    def method(self, y: Any) -> Any:
        return function(y)


class B:
    def __init__(self, z: Any) -> None:
        self.z = z

        class Internal:
            def internal_method(s, w: Any) -> Any:  # pylint: disable=no-self-argument
                return self.z + w

        self.internal = Internal()

    def internal_method(self, w: Any) -> Any:
        return self.internal.internal_method(w)

    @staticmethod
    def call(x: Any, y: Any) -> Any:
        return inside(x, y)


def main() -> None:
    a = A()
    result = a.method(10)
    print("Result:", result)


if __name__ == "__main__":
    main()
