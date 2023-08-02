# photoDBClient

## setup
```
git clone https://gitlab.cern.ch/cmsphiitrackeriihe/photoDBClient.git
cd photoDBClient
pip3 install --editable .
```
This will make the package available on your system (more info related to the `setuptools` library [here](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)).

The option `--editable` in the `pip` install ensures the package is setup in development mode.
Thus changes to the source code will not require to rebuild and reinstall.
If this is not desirable, just omit the `--editable` option.

Copy paste the `.photodb.example` into `.photodb`.
```
cd photoDBClient
cp .photodb.example .photodb
```

Edit `.photodb` by filling in the correct credentials example:
```
USERNAME=MyUserName
PASSWORD=super_secret
```