# Ansible Group YAML inventory
> An easy inventory YAML syntax for multi group hosts

## Context
Have you already tried to structure an Ansible inventory? 
But what if a host must be listed in multiple groups?
* A group to describe the location (Europe > Belgium, Asia > Japan, etc.)
* A group to describe the usage (Backup, DNS, etc)
* A group to describe the stage (prod, staging, dev, etc.)
* ...

Regular YAML file will allow it but requires a lot of duplication
and is painful to maintain
```yml
# Simplified, groups in UPPERCASE, hosts in lowercase
ALL:
  EU:
    BELGIUM:
      backup01:
  BACKUP:
    # The host must be listed in all the groups
    backup01:
```

Instead, you now get a new Inventory structure
```yml
groups: # describe your group hierarchy
hosts:
  backup01:
    vars: {}
    groups: [backups, be]
```
