import os
import logging
import subprocess
import re
import json
from typing import Any

from svdsuite.model.process import (
    Peripheral,
    Field,
    EnumeratedValueContainer,
    IEnumeratedValue,
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
    elif data_type.lower() == "uint8_t":
        return DataTypeType.UINT8_T
    elif data_type.lower() == "uint16_t":
        return DataTypeType.UINT16_T
    elif data_type.lower() == "uint32_t":
        return DataTypeType.UINT32_T
    elif data_type.lower() == "uint64_t":
        return DataTypeType.UINT64_T
    elif data_type.lower() == "int8_t":
        return DataTypeType.INT8_T
    elif data_type.lower() == "int16_t":
        return DataTypeType.INT16_T
    elif data_type.lower() == "int32_t":
        return DataTypeType.INT32_T
    elif data_type.lower() == "int64_t":
        return DataTypeType.INT64_T
    elif data_type.lower() == "uint8_t *":
        return DataTypeType.UINT8_T_PTR
    elif data_type.lower() == "uint16_t *":
        return DataTypeType.UINT16_T_PTR
    elif data_type.lower() == "uint32_t *":
        return DataTypeType.UINT32_T_PTR
    elif data_type.lower() == "uint64_t *":
        return DataTypeType.UINT64_T_PTR
    elif data_type.lower() == "int8_t *":
        return DataTypeType.INT8_T_PTR
    elif data_type.lower() == "int16_t *":
        return DataTypeType.INT16_T_PTR
    elif data_type.lower() == "int32_t *":
        return DataTypeType.INT32_T_PTR
    elif data_type.lower() == "int64_t *":
        return DataTypeType.INT64_T_PTR

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
    def __init__(self, json_output: str) -> None:
        try:
            self.data = json.loads(json_output)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON output from svdconv: %s", e)
            self.data = None

    def parse(self) -> list[Peripheral]:
        if self.data is None:
            return []

        peripherals: list[Peripheral] = []
        for peripheral in self.data:
            peripherals.append(
                Peripheral(
                    name=peripheral["name"],
                    version=peripheral["version"] or None,
                    description=None,
                    alternate_peripheral=peripheral["alternatePeripheral"] or None,
                    group_name=peripheral["groupName"] or None,
                    prepend_to_name=peripheral["prependToName"] or None,
                    append_to_name=peripheral["appendToName"] or None,
                    header_struct_name=peripheral["headerStructName"] or None,
                    disable_condition=(
                        None if peripheral["disableCondition"] == "NULL" else peripheral["disableCondition"]
                    ),
                    base_address=peripheral["baseAddress"],
                    address_blocks=self._parse_address_blocks(peripheral["addressBlocks"]),
                    interrupts=self._parse_interrupts(peripheral["interrupts"]),
                    parsed=None,  # type: ignore
                    size=peripheral["sizeEffective"],
                    access=_get_access_type(peripheral["access"]),
                    protection=_get_protection_type(peripheral["protection"]),
                    reset_value=peripheral["resetValue"],
                    reset_mask=peripheral["resetMask"],
                    end_address=0,
                    end_address_effective=0,
                    peripheral_size=0,
                    peripheral_size_effective=0,
                    registers_clusters=self._parse_registers_clusters(peripheral["registersClusters"]),
                    registers=[],
                )
            )

        return sorted(peripherals, key=lambda x: (x.base_address, x.name))

    def _parse_address_blocks(self, address_blocks: list[dict[str, Any]]) -> list[AddressBlock]:
        result: list[AddressBlock] = []
        for addr_block in address_blocks:
            result.append(
                AddressBlock(
                    offset=addr_block["offset"],
                    size=addr_block["size"],
                    usage=_get_addr_block_usage(addr_block["usage"]),
                    protection=_get_protection_type(addr_block["protection"]),
                    parsed=None,  # type: ignore
                )
            )

        return sorted(result, key=lambda x: x.offset)

    def _parse_interrupts(self, interrupts: list[dict[str, Any]]) -> list[Interrupt]:
        result: list[Interrupt] = []
        for interrupt in interrupts:
            result.append(
                Interrupt(
                    name=interrupt["name"],
                    description=None,
                    value=interrupt["value"],
                    parsed=None,  # type: ignore
                )
            )

        return sorted(result, key=lambda x: x.value)

    def _parse_registers_clusters(self, registers_clusters: list[dict[str, Any]]) -> list[Register | Cluster]:
        def sort_key(reg_cluster: Cluster | Register) -> tuple[int, tuple[int, str], str]:
            # Get alternate_group if it exists; default to None if not (e.g. for Clusters)
            alt = getattr(reg_cluster, "alternate_group", None)
            # If alt is None, return (0, '') so that None sorts before any string; else (1, alt)
            alt_key = (0, "") if alt is None else (1, alt)
            return (reg_cluster.base_address, alt_key, reg_cluster.name)

        result: list[Register | Cluster] = []
        for reg_cluster in registers_clusters:
            if reg_cluster["type"] == "register":
                result.append(self._parse_register(reg_cluster))
            elif reg_cluster["type"] == "cluster":
                result.append(self._parse_cluster(reg_cluster))
            else:
                raise NotImplementedError(f"Unknown type: {reg_cluster['type']}")

        return sorted(result, key=sort_key)

    def _parse_register(self, register: dict[str, Any]) -> Register:
        return Register(
            name=register["name"],
            display_name=register["displayName"] or None,
            description=None,
            alternate_group=register["alternateGroup"] or None,
            alternate_register=register["alternateRegister"] or None,
            address_offset=register["addressOffset"],
            data_type=_get_data_type(register["dataType"]),
            modified_write_values=_get_modified_write_value(register["modifiedWriteValues"]),
            write_constraint=None,
            read_action=_get_read_action(register["readAction"]),
            parsed=None,  # type: ignore
            size=register["sizeEffective"],
            access=_get_access_type(register["access"]),
            protection=_get_protection_type(register["protection"]),
            reset_value=register["resetValue"],
            reset_mask=register["resetMask"],
            base_address=register["absoluteAddress"],
            fields=self._parse_fields(register["fields"]),
        )

    def _parse_cluster(self, cluster: dict[str, Any]) -> Cluster:
        return Cluster(
            name=cluster["name"],
            description=None,
            alternate_cluster=cluster["alternateCluster"] or None,
            header_struct_name=cluster["headerStructName"] or None,
            address_offset=cluster["addressOffset"],
            parsed=None,  # type: ignore
            size=cluster["sizeEffective"],
            access=_get_access_type(cluster["access"]),
            protection=_get_protection_type(cluster["protection"]),
            reset_value=cluster["resetValue"],
            reset_mask=cluster["resetMask"],
            registers_clusters=self._parse_registers_clusters(cluster["registersClusters"]),
            base_address=cluster["absoluteAddress"],
            end_address=0,
            cluster_size=0,
        )

    def _parse_fields(self, fields: list[dict[str, Any]]) -> list[Field]:
        result: list[Field] = []
        for field in fields:
            bit_offset = field["bitOffset"]
            bit_width = field["bitWidth"]
            result.append(
                Field(
                    name=field["name"],
                    description=None,
                    bit_offset=bit_offset,
                    bit_width=bit_width,
                    lsb=bit_offset,
                    msb=bit_offset + bit_width - 1,
                    access=_get_access_type(field["access"]),
                    modified_write_values=_get_modified_write_value(field["modifiedWriteValues"]),
                    write_constraint=None,
                    read_action=_get_read_action(field["readAction"]),
                    enumerated_value_containers=self._parse_enum_value_containers(
                        field["enumContainers"], bit_offset, bit_offset + bit_width - 1
                    ),
                    bit_range=(bit_offset + bit_width - 1, bit_offset),
                    parsed=None,  # type: ignore
                )
            )

        return sorted(result, key=lambda x: (x.lsb, x.name))

    def _parse_enum_value_containers(
        self, enum_containers: list[dict[str, Any]], lsb: int, msb: int
    ) -> list[EnumeratedValueContainer]:
        result: list[EnumeratedValueContainer] = []
        for enum_container in enum_containers:
            enum_container_obj = EnumeratedValueContainer(
                name=enum_container["name"] or None,
                header_enum_name=enum_container["headerEnumName"] or None,
                usage=_get_enum_usage(enum_container["usage"]),
                enumerated_values=self._parse_enumerated_values(enum_container["enumeratedValues"], lsb, msb),
                parsed=None,  # type: ignore
            )

            enum_container_obj.enumerated_values = sorted(enum_container_obj.enumerated_values, key=lambda x: x.value)

            result.append(enum_container_obj)

        return result

    def _parse_enumerated_values(
        self, enumerated_values: list[dict[str, Any]], lsb: int, msb: int
    ) -> list[EnumeratedValue]:
        default_enum = None
        result: list[IEnumeratedValue] = []
        for enum_value in enumerated_values:
            enum_obj = IEnumeratedValue(
                name=enum_value["name"],
                description=None,
                value=int(enum_value["value"].replace("0b", ""), 2),
                is_default=enum_value["isDefault"],
                parsed=None,  # type: ignore
            )

            if enum_obj.is_default:
                default_enum = enum_obj
                enum_obj.value = None

            result.append(enum_obj)

        if default_enum is not None:
            result = self._extend_enumerated_values_with_default(result, default_enum, lsb, msb)

        enumerated_values_list: list[EnumeratedValue] = []
        for enum_value in result:
            if enum_value.value is None:
                raise ValueError("Enumerated value is None")

            enumerated_values_list.append(EnumeratedValue.from_intermediate_enum_value(enum_value, enum_value.value))

        return enumerated_values_list

    def _extend_enumerated_values_with_default(
        self, enumerated_values: list[IEnumeratedValue], default: IEnumeratedValue, lsb: int, msb: int
    ) -> list[IEnumeratedValue]:
        covered_values = {value.value for value in enumerated_values if value.value is not None}
        all_possible_values = set(range(pow(2, msb - lsb + 1)))

        uncovered_values = all_possible_values - covered_values

        for value in uncovered_values:
            enumerated_values.append(
                IEnumeratedValue(
                    name=f"{default.name}_{value}",
                    description=None,
                    value=value,
                    is_default=False,
                    parsed=default.parsed,
                )
            )

        return [value for value in enumerated_values if not value.is_default]


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

    json_output = run_svdconv(svd_path, ["--debug-output-json", "--quiet"])
    parser = SVDConvParser(json_output)

    return parser.parse()
