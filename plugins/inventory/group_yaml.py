import os
from collections.abc import MutableMapping

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.module_utils.six import string_types
from ansible.plugins.inventory import BaseFileInventoryPlugin

NoneType = type(None)

DOCUMENTATION = r'''
    name: Multi group YAML inventory
    plugin_type: inventory
    author:
        - Raphaël Joie (@raphaeljoie)
    short_description:
    description:
        - list hosts and group separate
    options:
        groups:
            description: the hosts.
            required: false
            type: dict
        hosts:
            description: the hosts.
            required: True
        plugin:
            description: Name of the plugin
            required: true
            choices: ['group_yaml']
        yaml_extensions:
            description: list of 'valid' extensions for files containing YAML
            type: list
            elements: string
            default: ['.yaml', '.yml', '.json']
            env:
              - name: ANSIBLE_YAML_FILENAME_EXT
              - name: ANSIBLE_INVENTORY_PLUGIN_EXTS
            ini:
              - key: yaml_valid_extensions
                section: defaults
              - section: inventory_plugin_yaml
                key: yaml_valid_extensions

    requirements:
        - python >= 3.4'''


class InventoryModule(BaseFileInventoryPlugin):
    NAME = 'group_yaml'

    def __init__(self):
        super(InventoryModule, self).__init__()

    def verify_file(self, path):
        """ return true/false if this is possibly a valid file for this plugin to consume """
        valid = False
        if super(InventoryModule, self).verify_file(path):
            file_name, ext = os.path.splitext(path)
            if not ext or ext in self.get_option('yaml_extensions'):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        # this method will parse 'common format' inventory sources and
        # update any options declared in DOCUMENTATION as needed
        config = self._read_config_data(path)

        try:
            data = self.loader.load_from_file(path, cache=False)
        except Exception as e:
            raise AnsibleParserError(e)

        if not data:
            raise AnsibleParserError('Parsed empty YAML file')
        elif not isinstance(data, MutableMapping):
            raise AnsibleParserError(
                'YAML inventory has invalid structure, it should be a dictionary, got: %s' % type(data))
        elif data.get('plugin') != InventoryModule.NAME:
            raise AnsibleParserError('Expected a ' + InventoryModule.NAME + ' plugin yaml file')
        elif not isinstance(data.get('hosts'), (list, MutableMapping, NoneType)):
            raise AnsibleParserError('Expected hosts to be a list or a dictionary, got: %s' % type(data.get('hosts')))

        if isinstance(data, MutableMapping):
            # ensure groups
            groups = data.get('groups')
            if groups is None:
                self.display.warning('Skipping groups')
            elif isinstance(groups, MutableMapping):
                for group_name in groups:
                    self._parse_group(group_name, groups[group_name])
            else:
                raise AnsibleParserError('Invalid')
            hosts = data.get('hosts')
            if isinstance(hosts, NoneType):
                self.display.warning('empty hosts')
            elif isinstance(hosts, MutableMapping):
                for host_name in hosts:
                    self._parse_host(host_name, hosts[host_name])
            else:
                raise AnsibleParserError('')
        else:
            raise AnsibleParserError("Invalid data from file, expected dictionary and got:\n\n%s" % to_native(data))

    def _parse_group(self, group, group_data):
        try:
            group = self.inventory.add_group(group)
        except AnsibleError as e:
            raise AnsibleParserError("Unable to add group %s: %s" % (group, to_text(e)))

        if group_data is not None:
            # make sure they are dicts
            for section in ['vars', 'children']:
                if section in group_data:
                    # convert strings to dicts as these are allowed
                    if isinstance(group_data[section], string_types):
                        group_data[section] = {group_data[section]: None}

                    if not isinstance(group_data[section], (MutableMapping, NoneType)):  # type: ignore[misc]
                        raise AnsibleParserError(
                            'Invalid "%s" entry for "%s" group, requires a dictionary, found "%s" instead.' %
                            (section, group, type(group_data[section])))

            for key in group_data:

                if not isinstance(group_data[key], (MutableMapping, NoneType)):  # type: ignore[misc]
                    self.display.warning('Skipping key (%s) in group (%s) as it is not a mapping, it is a %s' % (
                    key, group, type(group_data[key])))
                    continue

                if isinstance(group_data[key], NoneType):  # type: ignore[misc]
                    self.display.vvv('Skipping empty key (%s) in group (%s)' % (key, group))
                elif key == 'vars':
                    for var in group_data[key]:
                        self.inventory.set_variable(group, var, group_data[key][var])
                elif key == 'children':
                    for subgroup in group_data[key]:
                        subgroup = self._parse_group(subgroup, group_data[key][subgroup])
                        self.inventory.add_child(group, subgroup)

                else:
                    self.display.warning(
                        'Skipping unexpected key (%s) in group (%s), only "vars", "children" and "hosts" are valid' % (
                        key, group))

        return group

    def _parse_host(self, host_pattern, host_data):
        """
        Each host key can be a pattern, try to process it and add variables as needed
        """
        try:
            (hostnames, port) = self._expand_hostpattern(host_pattern)
        except TypeError:
            raise AnsibleParserError(
                f"Host pattern {host_pattern} must be a string. Enclose integers/floats in quotation marks."
            )

        variables = host_data.get('vars', {})
        groups = host_data.get('groups', [])

        for host in hostnames:
            self.inventory.add_host(host, port=port)
            for k in variables:
                self.inventory.set_variable(host, k, variables[k])
            for g in groups:
                group = self.inventory.add_group(g)
                self.inventory.add_host(host, port=port, group=group)
