import logging
from svdsuite.model.process import (
    Peripheral,
    Interrupt,
    Register,
    Cluster,
    AddressBlock,
    Field,
    EnumeratedValueContainer,
    EnumeratedValue,
)

logger = logging.getLogger(__name__)


class Compare:
    def __init__(self, svdconv_peripherals: list[Peripheral], svdsuite_peripherals: list[Peripheral]):
        self._svdconv_peripherals = svdconv_peripherals
        self._svdsuite_peripherals = svdsuite_peripherals

    def compare(self) -> bool:
        return self._compare_peripherals()

    def _compare_peripherals(self) -> bool:
        for peri_c, peri_s in zip(self._svdconv_peripherals, self._svdsuite_peripherals):
            if peri_c.name != peri_s.name:
                logger.warning("Name mismatch: %s != %s", peri_c.name, peri_s.name)
                return False

            if peri_c.version != peri_s.version:
                logger.warning("Version mismatch: %s != %s", peri_c.version, peri_s.version)
                return False

            if peri_c.alternate_peripheral != peri_s.alternate_peripheral:
                logger.warning(
                    "Alternate peripheral mismatch: %s != %s", peri_c.alternate_peripheral, peri_s.alternate_peripheral
                )
                return False

            if peri_c.group_name != peri_s.group_name:
                logger.warning("Group name mismatch: %s != %s", peri_c.group_name, peri_s.group_name)
                return False

            if peri_c.prepend_to_name != peri_s.prepend_to_name:
                logger.warning("Prepend to name mismatch: %s != %s", peri_c.prepend_to_name, peri_s.prepend_to_name)
                return False

            if peri_c.append_to_name != peri_s.append_to_name:
                logger.warning("Append to name mismatch: %s != %s", peri_c.append_to_name, peri_s.append_to_name)
                return False

            if peri_c.header_struct_name != peri_s.header_struct_name:
                logger.warning(
                    "Header struct name mismatch: %s != %s", peri_c.header_struct_name, peri_s.header_struct_name
                )
                return False

            if peri_c.base_address != peri_s.base_address:
                logger.warning("Base address mismatch: %s != %s", peri_c.base_address, peri_s.base_address)
                return False

            if len(peri_c.address_blocks) != len(peri_s.address_blocks):
                logger.warning(
                    "Address blocks count mismatch: %s != %s", len(peri_c.address_blocks), len(peri_s.address_blocks)
                )
                return False

            if not self._compare_address_blocks(peri_c.address_blocks, peri_s.address_blocks):
                return False

            if len(peri_c.interrupts) != len(peri_s.interrupts):
                logger.warning("Interrupts count mismatch: %s != %s", len(peri_c.interrupts), len(peri_s.interrupts))
                return False

            if not self._compare_interrupts(peri_c.interrupts, peri_s.interrupts):
                return False

            if peri_c.size != peri_s.size:
                logger.warning("Size mismatch: %s != %s", peri_c.size, peri_s.size)
                return False

            if peri_c.access != peri_s.access:
                logger.warning("Access mismatch: %s != %s", peri_c.access, peri_s.access)
                return False

            if peri_c.protection != peri_s.protection:
                logger.warning("Protection mismatch: %s != %s", peri_c.protection, peri_s.protection)
                return False

            # Can't compare reset values and masks do to a bug in svdconv

            # if peri_c.reset_value != peri_s.reset_value:
            #     logger.warning("Reset value mismatch: %s != %s", peri_c.reset_value, peri_s.reset_value)
            #     return False

            # if peri_c.reset_mask != peri_s.reset_mask:
            #     logger.warning("Reset mask mismatch: %s != %s", peri_c.reset_mask, peri_s.reset_mask)
            #     return False

            if len(peri_c.registers_clusters) != len(peri_s.registers_clusters):
                logger.warning(
                    "Registers clusters count mismatch: %s != %s",
                    len(peri_c.registers_clusters),
                    len(peri_s.registers_clusters),
                )
                return False

            if not self._compare_registers_clusters(peri_c.registers_clusters, peri_s.registers_clusters):
                return False

        return True

    def _compare_address_blocks(
        self, address_blocks_c: list[AddressBlock], address_blocks_s: list[AddressBlock]
    ) -> bool:
        for ab_c, ab_s in zip(address_blocks_c, address_blocks_s):
            if ab_c.offset != ab_s.offset:
                logger.warning("Address block offset mismatch: %s != %s", ab_c.offset, ab_s.offset)
                return False

            if ab_c.size != ab_s.size:
                logger.warning("Address block size mismatch: %s != %s", ab_c.size, ab_s.size)
                return False

            if ab_c.usage != ab_s.usage:
                logger.warning("Address block usage mismatch: %s != %s", ab_c.usage, ab_s.usage)
                return False

            if ab_c.protection != ab_s.protection:
                logger.warning("Address block protection mismatch: %s != %s", ab_c.protection, ab_s.protection)
                return False

        return True

    def _compare_interrupts(self, interrupts_c: list[Interrupt], interrupts_s: list[Interrupt]) -> bool:
        for int_c, int_s in zip(interrupts_c, interrupts_s):
            if int_c.name != int_s.name:
                logger.warning("Interrupt name mismatch: %s != %s", int_c.name, int_s.name)
                return False

            if int_c.value != int_s.value:
                logger.warning("Interrupt value mismatch: %s != %s", int_c.value, int_s.value)
                return False

        return True

    def _compare_registers_clusters(
        self, registers_clusters_c: list[Register | Cluster], registers_clusters_s: list[Register | Cluster]
    ) -> bool:
        for reg_cluster_c, reg_cluster_s in zip(registers_clusters_c, registers_clusters_s):
            if isinstance(reg_cluster_c, Register) and isinstance(reg_cluster_s, Register):
                if not self._compare_register(reg_cluster_c, reg_cluster_s):
                    return False
            elif isinstance(reg_cluster_c, Cluster) and isinstance(reg_cluster_s, Cluster):
                if not self._compare_cluster(reg_cluster_c, reg_cluster_s):
                    return False
            else:
                logger.warning("Register/Cluster type mismatch: %s != %s", type(reg_cluster_c), type(reg_cluster_s))
                return False

        return True

    def _compare_register(self, register_c: Register, register_s: Register) -> bool:
        if register_c.name != register_s.name:
            logger.warning("Register name mismatch: %s != %s", register_c.name, register_s.name)
            return False

        if register_c.display_name != register_s.display_name:
            logger.warning("Register display name mismatch: %s != %s", register_c.display_name, register_s.display_name)
            return False

        if register_c.alternate_group != register_s.alternate_group:
            logger.warning(
                "Register alternate group mismatch: %s != %s", register_c.alternate_group, register_s.alternate_group
            )
            return False

        if register_c.alternate_register != register_s.alternate_register:
            logger.warning(
                "Register alternate register mismatch: %s != %s",
                register_c.alternate_register,
                register_s.alternate_register,
            )
            return False

        if register_c.address_offset != register_s.address_offset:
            logger.warning(
                "Register address offset mismatch: %s != %s", register_c.address_offset, register_s.address_offset
            )
            return False

        if register_c.data_type != register_s.data_type:
            logger.warning("Register data type mismatch: %s != %s", register_c.data_type, register_s.data_type)
            return False

        if register_c.modified_write_values != register_s.modified_write_values:
            logger.warning(
                "Register modified write values mismatch: %s != %s",
                register_c.modified_write_values,
                register_s.modified_write_values,
            )
            return False

        if register_c.read_action != register_s.read_action:
            logger.warning("Register read action mismatch: %s != %s", register_c.read_action, register_s.read_action)
            return False

        if register_c.size != register_s.size:
            logger.warning("Register size mismatch: %s != %s", register_c.size, register_s.size)
            return False

        if register_c.access != register_s.access:
            logger.warning("Register access mismatch: %s != %s", register_c.access, register_s.access)
            return False

        if register_c.protection != register_s.protection:
            logger.warning("Register protection mismatch: %s != %s", register_c.protection, register_s.protection)
            return False

        # Can't compare reset values and masks do to a bug in svdconv

        # if register_c.reset_value != register_s.reset_value:
        #     logger.warning("Register reset value mismatch: %s != %s", register_c.reset_value, register_s.reset_value)
        #     return False

        # if register_c.reset_mask != register_s.reset_mask:
        #     logger.warning("Register reset mask mismatch: %s != %s", register_c.reset_mask, register_s.reset_mask)
        #     return False

        if len(register_c.fields) != len(register_s.fields):
            logger.warning("Fields count mismatch: %s != %s", len(register_c.fields), len(register_s.fields))
            return False

        if not self._compare_fields(register_c.fields, register_s.fields):
            return False

        if register_c.base_address != register_s.base_address:
            logger.warning("Register base address mismatch: %s != %s", register_c.base_address, register_s.base_address)
            return False

        return True

    def _compare_cluster(self, cluster_c: Cluster, cluster_s: Cluster) -> bool:
        if cluster_c.name != cluster_s.name:
            logger.warning("Cluster name mismatch: %s != %s", cluster_c.name, cluster_s.name)
            return False

        if cluster_c.alternate_cluster != cluster_s.alternate_cluster:
            logger.warning(
                "Cluster alternate cluster mismatch: %s != %s", cluster_c.alternate_cluster, cluster_s.alternate_cluster
            )
            return False

        if cluster_c.header_struct_name != cluster_s.header_struct_name:
            logger.warning(
                "Cluster header struct name mismatch: %s != %s",
                cluster_c.header_struct_name,
                cluster_s.header_struct_name,
            )
            return False

        if cluster_c.address_offset != cluster_s.address_offset:
            logger.warning(
                "Cluster address offset mismatch: %s != %s", cluster_c.address_offset, cluster_s.address_offset
            )
            return False

        if cluster_c.size != cluster_s.size:
            logger.warning("Cluster size mismatch: %s != %s", cluster_c.size, cluster_s.size)
            return False

        if cluster_c.access != cluster_s.access:
            logger.warning("Cluster access mismatch: %s != %s", cluster_c.access, cluster_s.access)
            return False

        if cluster_c.protection != cluster_s.protection:
            logger.warning("Cluster protection mismatch: %s != %s", cluster_c.protection, cluster_s.protection)
            return False

        # Can't compare reset values and masks do to a bug in svdconv

        # if cluster_c.reset_value != cluster_s.reset_value:
        #     logger.warning("Cluster reset value mismatch: %s != %s", cluster_c.reset_value, cluster_s.reset_value)
        #     return False

        # if cluster_c.reset_mask != cluster_s.reset_mask:
        #     logger.warning("Cluster reset mask mismatch: %s != %s", cluster_c.reset_mask, cluster_s.reset_mask)
        #     return False

        if len(cluster_c.registers_clusters) != len(cluster_s.registers_clusters):
            logger.warning(
                "Registers clusters count mismatch: %s != %s",
                len(cluster_c.registers_clusters),
                len(cluster_s.registers_clusters),
            )
            return False

        if not self._compare_registers_clusters(cluster_c.registers_clusters, cluster_s.registers_clusters):
            return False

        if cluster_c.base_address != cluster_s.base_address:
            logger.warning("Cluster base address mismatch: %s != %s", cluster_c.base_address, cluster_s.base_address)
            return False

        return True

    def _compare_fields(self, fields_c: list[Field], fields_s: list[Field]) -> bool:
        for field_c, field_s in zip(fields_c, fields_s):
            if field_c.name != field_s.name:
                logger.warning("Field name mismatch: %s != %s", field_c.name, field_s.name)
                return False

            if field_c.lsb != field_s.lsb:
                logger.warning("Field lsb mismatch: %s != %s", field_c.lsb, field_s.lsb)
                return False

            if field_c.msb != field_s.msb:
                logger.warning("Field msb mismatch: %s != %s", field_c.msb, field_s.msb)
                return False

            if field_c.bit_offset != field_s.bit_offset:
                logger.warning("Field bit offset mismatch: %s != %s", field_c.bit_offset, field_s.bit_offset)
                return False

            if field_c.bit_width != field_s.bit_width:
                logger.warning("Field bit width mismatch: %s != %s", field_c.bit_width, field_s.bit_width)
                return False

            if field_c.bit_range != field_s.bit_range:
                logger.warning("Field bit range mismatch: %s != %s", field_c.bit_range, field_s.bit_range)
                return False

            if field_c.modified_write_values != field_s.modified_write_values:
                logger.warning(
                    "Field modified write values mismatch: %s != %s",
                    field_c.modified_write_values,
                    field_s.modified_write_values,
                )
                return False

            if field_c.read_action != field_s.read_action:
                logger.warning("Field read action mismatch: %s != %s", field_c.read_action, field_s.read_action)
                return False

            if field_c.access != field_s.access:
                logger.warning("Field access mismatch: %s != %s", field_c.access, field_s.access)
                return False

            if len(field_c.enumerated_value_containers) != len(field_s.enumerated_value_containers):
                logger.warning(
                    "Enumerated value containers count mismatch: %s != %s",
                    len(field_c.enumerated_value_containers),
                    len(field_s.enumerated_value_containers),
                )
                return False

            if not self._compare_enumerated_value_containers(
                field_c.enumerated_value_containers, field_s.enumerated_value_containers
            ):
                return False

        return True

    def _compare_enumerated_value_containers(
        self, evcs_c: list[EnumeratedValueContainer], evcs_s: list[EnumeratedValueContainer]
    ) -> bool:
        for evc_c, evc_s in zip(evcs_c, evcs_s):
            if evc_c.name != evc_s.name:
                logger.warning("Enumerated value container name mismatch: %s != %s", evc_c.name, evc_s.name)
                return False

            if evc_c.header_enum_name != evc_s.header_enum_name:
                logger.warning(
                    "Enumerated value container header enum name mismatch: %s != %s",
                    evc_c.header_enum_name,
                    evc_s.header_enum_name,
                )
                return False

            if evc_c.usage != evc_s.usage:
                logger.warning("Enumerated value container usage mismatch: %s != %s", evc_c.usage, evc_s.usage)
                return False

            if len(evc_c.enumerated_values) != len(evc_s.enumerated_values):
                logger.warning(
                    "Enumerated values count mismatch: %s != %s",
                    len(evc_c.enumerated_values),
                    len(evc_s.enumerated_values),
                )
                return False

            if not self._compare_enumerated_values(evc_c.enumerated_values, evc_s.enumerated_values):
                return False

        return True

    def _compare_enumerated_values(self, evs_c: list[EnumeratedValue], evs_s: list[EnumeratedValue]) -> bool:
        for ev_c, ev_s in zip(evs_c, evs_s):
            if ev_c.name != ev_s.name:
                logger.warning("Enumerated value name mismatch: %s != %s", ev_c.name, ev_s.name)
                return False

            if ev_c.value != ev_s.value:
                logger.warning("Enumerated value value mismatch: %s != %s", ev_c.value, ev_s.value)
                return False

            if ev_c.is_default != ev_s.is_default:
                logger.warning("Enumerated value is_default mismatch: %s != %s", ev_c.is_default, ev_s.is_default)
                return False

        return True
