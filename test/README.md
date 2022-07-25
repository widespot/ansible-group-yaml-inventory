```
mkdir ../build
ansible-galaxy collection build --force --output-path ../build ../
ansible-galaxy install -r requirements.yml
ansible-inventory --list
```
