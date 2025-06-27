# Install Qt6 Library 

```
sudo apt update
sudo apt remove xdg-desktop-portal-gtk
sudo apt purge $(dpkg -l |awk '/^rc/ { print $2}' )
sudo apt autoremove --purge
sudo apt clean
sudo apt install libQt6
sudo apt install qt6-base-dev qt6-tools-dev qt6-tools-dev-tools
sudo apt install libxcb-cursor0 libx11-xcb1 libxcb1 libxcb-render0 libxcb-shape0 libxcb-xfixes0 
sudo apt install libxcb-xinerama0 libxcb-xinerama0-dev libxkbcommon-x11-0
```
# Install required python modules
```
python3 -m venv PyEnv
source PyEnv/bin/activate

pip install --upgrade pip
pip install setuptools
pip install lightweight-charts
pip install PyQt6
pip install QtPy
pip install PyQtWebEngine
pip install dotenv
pip install protobuf==5.29.3
```

# Instal IBJts
Dowonload ***twsapi_macunix.1037.02.zip***
```
curl https://interactivebrokers.github.io/downloads/twsapi_macunix.1037.02.zip
unzip twsapi_macunix.1037.02.zip
cd IBJts/source/pythonclient
python setup.py install
```



