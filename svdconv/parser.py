import re
import os
import logging
import subprocess

from svdsuite.model.process import (
    Peripheral,
    Field,
    EnumeratedValueContainer,
    EnumeratedValue,
    AddressBlock,
    Register,
    Cluster,
    Interrupt,
)
from svdsuite.model.types import (
    AccessType,
    ProtectionStringType,
    EnumeratedTokenType,
    ModifiedWriteValuesType,
    ReadActionType,
    DataTypeType,
    EnumUsageType,
)

logger = logging.getLogger(__name__)

WHITESPACES = 4


def _get_access_type(access: str) -> AccessType:
    if access == "UNDEF":
        raise NotImplementedError
    elif access == "READ_ONLY":
        return AccessType.READ_ONLY
    elif access == "WRITE_ONLY":
        return AccessType.WRITE_ONLY
    elif access == "READ_WRITE":
        return AccessType.READ_WRITE
    elif access == "WRITE_ONCE":
        return AccessType.WRITE_ONCE
    elif access == "READ_WRITE_ONCE":
        return AccessType.READ_WRITE_ONCE
    elif access == "END":
        raise NotImplementedError
    else:
        raise NotImplementedError


def _get_protection_type(protection: str) -> ProtectionStringType:
    if protection == "UNDEF":
        return ProtectionStringType.ANY
    elif protection == "SECURE":
        return ProtectionStringType.SECURE
    elif protection == "NONSECURE":
        return ProtectionStringType.NON_SECURE
    elif protection == "PRIVILEGED":
        return ProtectionStringType.PRIVILEGED
    else:
        raise NotImplementedError


def _get_addr_block_usage(usage: str) -> EnumeratedTokenType:
    if usage == "UNDEF":
        raise NotImplementedError(f"No matching AddrBlockUsage for: {usage}")
    elif usage == "REGISTERS":
        return EnumeratedTokenType.REGISTERS
    elif usage == "BUFFER":
        return EnumeratedTokenType.BUFFER
    elif usage == "RESERVED":
        return EnumeratedTokenType.RESERVED
    else:
        raise NotImplementedError(f"No matching AddrBlockUsage for: {usage}")


def _get_modified_write_value(mod_write_val: str) -> ModifiedWriteValuesType:
    if mod_write_val == "undefined":
        return ModifiedWriteValuesType.MODIFY
    elif mod_write_val == "oneToClear":
        return ModifiedWriteValuesType.ONE_TO_CLEAR
    elif mod_write_val == "oneToSet":
        return ModifiedWriteValuesType.ONE_TO_SET
    elif mod_write_val == "oneToToggle":
        return ModifiedWriteValuesType.ONE_TO_TOGGLE
    elif mod_write_val == "zeroToClear":
        return ModifiedWriteValuesType.ZERO_TO_CLEAR
    elif mod_write_val == "zeroToSet":
        return ModifiedWriteValuesType.ZERO_TO_SET
    elif mod_write_val == "zeroToToggle":
        return ModifiedWriteValuesType.ZERO_TO_TOGGLE
    elif mod_write_val == "clear":
        return ModifiedWriteValuesType.CLEAR
    elif mod_write_val == "set":
        return ModifiedWriteValuesType.SET
    elif mod_write_val == "modify":
        return ModifiedWriteValuesType.MODIFY
    else:
        raise NotImplementedError(f"No matching ModifiedWriteValuesType for: {mod_write_val}")


def _get_read_action(action: str) -> ReadActionType | None:
    if action == "UNDEF":
        return None
    elif action == "CLEAR":
        return ReadActionType.CLEAR
    elif action == "SET":
        return ReadActionType.SET
    elif action == "MODIFY":
        return ReadActionType.MODIFY
    elif action == "MODIFEXT":
        return ReadActionType.MODIFY_EXTERNAL
    else:
        raise NotImplementedError(f"No matching ReadActionType for: {action}")


def _get_data_type(data_type: str) -> DataTypeType | None:
    if data_type == "":
        return None

    raise NotImplementedError(f"No matching DataTypeType for: {data_type}")


def _get_enum_usage(usage: str) -> EnumUsageType:
    if usage == "UNDEF":
        return EnumUsageType.READ_WRITE
    elif usage == "READ":
        return EnumUsageType.READ
    elif usage == "WRITE":
        return EnumUsageType.WRITE
    elif usage == "READWRITE":
        return EnumUsageType.READ_WRITE
    else:
        raise NotImplementedError(f"No matching EnumUsageType for: {usage}")


class SVDConvParser:
    def __init__(self, lines: list[str]):
        self.lines = lines

    def parse(self) -> list[Peripheral]:
        # Split the output into peripheral blocks using a separator (e.g. a line with many '^')
        peripheral_blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in self.lines:
            if "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^" in line:
                if current_block:
                    peripheral_blocks.append(current_block)
                    current_block = []
            else:
                if line.strip() == "":  # Skip empty lines and lines which only contain whitespace
                    continue

                current_block.append(line)
        if current_block:
            peripheral_blocks.append(current_block)

        peripherals = [self.parse_peripheral(block) for block in peripheral_blocks]
        return sorted(peripherals, key=lambda p: (p.base_address, p.name))

    def parse_peripheral(self, lines: list[str]) -> "Peripheral":
        # The first line should be something like "=== Peripheral <Name> ==="
        header_line = lines[0].strip()
        m = re.match(r"=== Peripheral (.+) ===", header_line)
        name = m.group(1).strip() if m else "UnknownPeripheral"
        data = {"name": name}
        index = 1
        # Read lines until a new section (e.g., "Address Block:", "Interrupt:" or "===") begins.
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("Address Block:") or line.startswith("Interrupt:") or line.startswith("==="):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1

        # Parse Address Blocks and Interrupts
        address_blocks: list[AddressBlock] = []
        interrupts: list[Interrupt] = []
        registers_clusters: list[Register | Cluster] = []
        while index < len(lines):
            line = lines[index]
            if line.strip().startswith("Address Block:"):
                block, index = self.parse_address_block(lines, index)
                address_blocks.append(block)
            elif line.strip().startswith("Interrupt:"):
                intr, index = self.parse_interrupt(lines, index)
                interrupts.append(intr)
            elif line.strip().startswith("==="):
                element, index = self.parse_register_or_cluster(lines, index)
                if element is not None:
                    registers_clusters.append(element)
            else:
                index += 1

        peripheral = Peripheral(
            name=data.get("name", name),
            version=data.get("version") or None,
            description=None,
            alternate_peripheral=data.get("alternatePeripheral") or None,
            group_name=data.get("groupName") or None,
            prepend_to_name=data.get("prependToName") or None,
            append_to_name=data.get("appendToName") or None,
            header_struct_name=data.get("headerStructName") or None,
            disable_condition=None if data.get("disableCondition") == "NULL" else data.get("disableCondition"),
            base_address=int(data.get("baseAddress", "0").replace("0x", ""), 16) if "baseAddress" in data else 0,
            address_blocks=sorted(address_blocks, key=lambda ab: ab.offset),
            interrupts=sorted(interrupts, key=lambda intr: intr.value),
            parsed=None,  # type: ignore
            size=int(data.get("size effective", 0)),
            access=_get_access_type(data.get("access", "")),
            protection=_get_protection_type(data.get("protection", "")),
            reset_value=int(data.get("resetValue", "0").replace("0x", ""), 16) if "resetValue" in data else 0,
            reset_mask=int(data.get("resetMask", "0").replace("0x", ""), 16) if "resetMask" in data else 0,
            end_address=0,
            end_address_effective=0,
            peripheral_size=0,
            peripheral_size_effective=0,
            registers_clusters=sorted(registers_clusters, key=lambda rc: (rc.address_offset, rc.name)),
            registers=[],
        )
        return peripheral

    def parse_address_block(self, lines: list[str], index: int) -> tuple["AddressBlock", int]:
        # Skip the "Address Block:" line.
        index += 1
        block_data: dict[str, str] = {}
        while index < len(lines):
            if (
                lines[index].strip().startswith("Interrupt:")
                or lines[index].strip().startswith("Address Block:")
                or lines[index].strip().startswith("===")
            ):
                break
            key, value = lines[index].strip().split(":", 1)
            block_data[key.strip()] = value.strip()
            index += 1
        block = AddressBlock(
            offset=int(block_data.get("Offset", "0").replace("0x", ""), 16) if "Offset" in block_data else 0,
            size=int(block_data.get("Size", "0")),
            usage=_get_addr_block_usage(block_data.get("Usage", "")),
            protection=_get_protection_type(block_data.get("Protection", "")) or None,
            parsed=None,  # type: ignore
        )
        return block, index

    def parse_interrupt(self, lines: list[str], index: int) -> tuple["Interrupt", int]:
        # Skip the "Interrupt:" line.
        index += 1
        intr_data: dict[str, str] = {}
        while index < len(lines):
            if (
                lines[index].strip().startswith("Interrupt:")
                or lines[index].strip().startswith("Address Block:")
                or lines[index].strip().startswith("===")
            ):
                break
            key, value = lines[index].strip().split(":", 1)
            intr_data[key.strip()] = value.strip()
            index += 1
        intr = Interrupt(
            name=intr_data.get("Name", ""),
            description=None,
            value=int(intr_data.get("Value", "0")),
            parsed=None,  # type: ignore
        )
        return intr, index

    def parse_register_or_cluster(self, lines: list[str], index: int) -> tuple[None | Register | Cluster, int]:
        line = lines[index].strip()
        if line.startswith("=== Register"):
            reg, index = self.parse_register(lines, index)
            return reg, index
        elif line.startswith("=== Cluster"):
            cluster, index = self.parse_cluster(lines, index)
            return cluster, index
        else:
            index += 1
            return None, index

    def parse_register(self, lines: list[str], index: int) -> tuple["Register", int]:
        header_line = lines[index].strip()
        m = re.match(r"=== Register (.+?) \(with prepend & append: (.+?)\) ===", header_line)
        name = m.group(1).strip() if m else "UnknownRegister"
        data: dict[str, str] = {"name": name}
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("==="):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1
        reg = Register(
            name=data.get("name", name),
            display_name=data.get("displayName") or None,
            description=None,
            alternate_group=data.get("alternateGroup") or None,
            alternate_register=data.get("alternateRegister") or None,
            address_offset=int(data.get("addressOffset", "0").replace("0x", ""), 16) if "addressOffset" in data else 0,
            data_type=_get_data_type(data.get("dataType", "")) or None,
            modified_write_values=_get_modified_write_value(data.get("modifiedWriteValues", "")),
            write_constraint=None,
            read_action=_get_read_action(data.get("readAction", "")) or None,
            parsed=None,  # type: ignore
            size=int(data.get("size effective", "0")),
            access=_get_access_type(data.get("access", "")),
            protection=_get_protection_type(data.get("protection", "")),
            reset_value=int(data.get("resetValue", "0").replace("0x", ""), 16) if "resetValue" in data else 0,
            reset_mask=int(data.get("resetMask", "0").replace("0x", ""), 16) if "resetMask" in data else 0,
            base_address=(
                int(data.get("Absolute Address", "0").replace("0x", ""), 16) if "Absolute Address" in data else 0
            ),
            fields=[],
        )

        # If there are Fields listed directly under the register, parse them.
        while index < len(lines):
            if lines[index].strip().startswith("=== Field"):
                field_obj, index = self.parse_field(lines, index)
                reg.fields.append(field_obj)
            else:
                break

        reg.fields = sorted(reg.fields, key=lambda f: (f.lsb, f.name))

        return reg, index

    def get_current_depth(self, line: str) -> int:
        if not line.strip().startswith("==="):
            raise ValueError("Expected a new section to begin with '==='")

        whitespace_count = len(line) - len(line.lstrip())

        if whitespace_count % WHITESPACES != 0:
            raise ValueError("Unexpected indentation")

        return whitespace_count // WHITESPACES

    def parse_cluster(self, lines: list[str], index: int) -> tuple["Cluster", int]:
        cluster_depth = self.get_current_depth(lines[index])

        header_line = lines[index].strip()
        m = re.match(r"=== Cluster (.+) ===", header_line)
        name = m.group(1).strip() if m else "UnknownCluster"
        data = {"name": name}
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            if line.startswith("==="):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1
        registers_clusters: list[Register | Cluster] = []
        while index < len(lines):
            if index >= len(lines):
                break
            if lines[index].strip().startswith("==="):
                if self.get_current_depth(lines[index]) == cluster_depth:
                    break
                element, index = self.parse_register_or_cluster(lines, index)
                if element is not None:
                    registers_clusters.append(element)
            else:
                index += 1
        cluster = Cluster(
            name=data.get("name", name),
            description=None,
            alternate_cluster=data.get("alternateCluster") or None,
            header_struct_name=data.get("headerStructName") or None,
            address_offset=int(data.get("addressOffset", "0").replace("0x", ""), 16) if "addressOffset" in data else 0,
            parsed=None,  # type: ignore
            size=int(data.get("size effective", "0")),
            access=_get_access_type(data.get("access", "")),
            protection=_get_protection_type(data.get("protection", "")),
            reset_value=int(data.get("resetValue", "0").replace("0x", ""), 16) if "resetValue" in data else 0,
            reset_mask=int(data.get("resetMask", "0").replace("0x", ""), 16) if "resetMask" in data else 0,
            registers_clusters=sorted(registers_clusters, key=lambda rc: (rc.address_offset, rc.name)),
            base_address=(
                int(data.get("Absolute Address", "0").replace("0x", ""), 16) if "Absolute Address" in data else 0
            ),
            end_address=0,
            cluster_size=0,
        )
        return cluster, index

    def parse_field(self, lines: list[str], index: int) -> tuple[Field, int]:
        # Begins with a line like "=== Field <Name> ==="
        line = lines[index].strip()
        m = re.match(r"=== Field (.+) ===", line)
        field_name = m.group(1).strip() if m else "UnknownField"
        data = {"name": field_name}
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            # End the field block if an empty line or a new header is encountered.
            if not line or line.startswith("==="):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1
        bit_offset = int(data.get("bitOffset", "0"))
        bit_width = int(data.get("bitWidth", "0"))
        field_obj = Field(
            name=data.get("name", field_name),
            description=None,
            bit_offset=bit_offset,
            bit_width=bit_width,
            lsb=bit_offset,
            msb=bit_offset + bit_width - 1,
            access=_get_access_type(data.get("access", "")),
            modified_write_values=_get_modified_write_value(data.get("modifiedWriteValues", "")),
            write_constraint=None,
            read_action=_get_read_action(data.get("readAction", "")) or None,
            enumerated_value_containers=[],
            bit_range=(bit_offset + bit_width - 1, bit_offset),
            parsed=None,  # type: ignore
        )

        # Check for Enum Containers following the Field.
        while index < len(lines):
            if lines[index].strip().startswith("=== Enum Container:"):
                enum_container, index = self.parse_enum_container(lines, index, bit_offset, bit_offset + bit_width - 1)
                field_obj.enumerated_value_containers.append(enum_container)
            else:
                break

        return field_obj, index

    def _extend_enumerated_values_with_default(
        self, enumerated_values: list[EnumeratedValue], default: EnumeratedValue, lsb: int, msb: int
    ) -> list[EnumeratedValue]:
        covered_values = {value.value for value in enumerated_values if value.value is not None}
        all_possible_values = set(range(pow(2, msb - lsb + 1)))

        uncovered_values = all_possible_values - covered_values

        for value in uncovered_values:
            enumerated_values.append(
                EnumeratedValue(
                    name=f"{default.name}_{value}",
                    description=None,
                    value=value,
                    is_default=False,
                    parsed=default.parsed,
                )
            )

        return [value for value in enumerated_values if not value.is_default]

    def parse_enum_container(
        self, lines: list[str], index: int, lsb: int, msb: int
    ) -> tuple[EnumeratedValueContainer, int]:
        # Begins with a line like "=== Enum Container: <Name> ==="
        line = lines[index].strip()
        m = re.match(r"=== Enum Container: (.+) ===", line)
        container_name = m.group(1).strip() if m else None
        data: dict[str, str | None] = {"name": container_name}
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            if not line or line.startswith("===") or line.startswith("Enum:"):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1
        enum_container = EnumeratedValueContainer(
            name=data.get("name", container_name),
            header_enum_name=data.get("headerEnumName") or None,
            usage=_get_enum_usage(data.get("usage", "")),  # type: ignore
            enumerated_values=[],
            parsed=None,  # type: ignore
        )
        # Parse one or more Enum blocks if present.
        while index < len(lines):
            if lines[index].strip().startswith("Enum:"):
                enum_obj, index = self.parse_enum(lines, index)
                if enum_obj is not None:
                    enum_container.enumerated_values.append(enum_obj)
            else:
                break

        # If there is a default EnumeratedValue, extend the list of EnumeratedValues with all possible values.
        default_enum = next((ev for ev in enum_container.enumerated_values if ev.is_default), None)
        if default_enum is not None:
            enum_container.enumerated_values = self._extend_enumerated_values_with_default(
                enum_container.enumerated_values, default_enum, lsb, msb
            )

        enum_container.enumerated_values = sorted(
            enum_container.enumerated_values, key=lambda ev: ev.value if ev.value is not None else 0
        )

        return enum_container, index

    def parse_enum(self, lines: list[str], index: int) -> tuple[EnumeratedValue | None, int]:
        # The Enum block begins with "Enum:" and contains key/value pairs.
        line = lines[index].strip()
        if not line.startswith("Enum:"):
            return None, index
        data: dict[str, str] = {}
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            # End if an empty line or a new header is encountered.
            if not line or line.startswith("===") or re.match(r"^[^ ]", lines[index]) or line.startswith("Enum:"):
                break
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
            index += 1
        bin_value = data.get("value", "0")
        try:
            int_value = int(bin_value.replace("0b", ""), 2)
        except ValueError:
            int_value = 0
        enum_obj = EnumeratedValue(
            name=data.get("name", ""),
            description=None,
            value=int_value,
            is_default=data.get("isDefault", "false").lower() in ("true", "yes", "1"),
            parsed=None,  # type: ignore
        )

        if enum_obj.is_default:
            enum_obj.value = None

        return enum_obj, index


def run_svdconv(svd_path: str, args: None | list[str] = None) -> str:
    if args is None:
        args = []

    result = subprocess.run(
        [os.path.join(os.path.dirname(__file__), "svdconv"), svd_path] + args,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )

    return result.stdout


def get_error_warning_stats(svd_path: str) -> tuple[int, int]:
    pattern = r"Found (\d+) Error\(s\) and (\d+) Warning\(s\)"

    output = run_svdconv(svd_path)

    match = re.search(pattern, output)
    if match:
        return int(match.group(1)), int(match.group(2))
    else:
        raise ValueError("Could not find error and warning count in svdconv output")


def parse_svdconv_output(svd_path: str) -> None | list[Peripheral]:
    errors, _ = get_error_warning_stats(svd_path)

    if errors > 0:
        logger.error("Found %d errors in svdconv output for %s", errors, svd_path)
        return None

    debug_output = run_svdconv(svd_path, ["--debug-output", "--quiet"])
    lines = debug_output.splitlines()
    parser = SVDConvParser(lines)

    return parser.parse()
