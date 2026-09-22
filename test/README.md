```
mkdir ../build
python3 -m venv venv
source venv/bin/activate
pip install ansible-core 2.21.4
ansible-galaxy collection build --force --output-path ../build ../
ansible-galaxy install -r requirements.yml
ansible-inventory --list
```
