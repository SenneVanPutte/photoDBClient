# IIHE_picture_soft


## Installation
sudo yum install gvfs-gphoto2
sudo yum install snapd
sudo systemctl enable --now snapd.socket
sudo ln -s /var/lib/snapd/snap /snap
sudo snap install gphoto2

sudo yum localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm
sudo yum install ffmpeg ffmpeg-devel


sudo apt-get install gphoto2 v4l2loopback-utils v4l2loopback-dkms ffmpeg build-essential libelf-dev linux-headers-$(uname -r) unzip vlc 
