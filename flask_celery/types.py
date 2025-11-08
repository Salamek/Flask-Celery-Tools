"""Define custom types."""

CelerySerializable = str | int | float | bool | None | dict[str, "CelerySerializable"] | list["CelerySerializable"]
