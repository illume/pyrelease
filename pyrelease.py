"""Package is for python packages with only code and data.

*Please do not use this.*
*This is just an experiment so far.*

Often you have only a couple of python files, and you want to share them.


* Gather facts.
* Ask about required details.
    * Tell user to set up things (eg .pypirc, .gitconfig)
* Write out template.
* build build dist
* push

"""

import io
import os
import re
import ast
import imp
import tempfile

from configparser import ConfigParser
from email.utils import getaddresses
import subprocess
from fnmatch import fnmatchcase, fnmatch
from shutil import copyfile


class PyPiRc:
    """
    ~/.pypirc
    [simple_setup]
    author = My Name Is
    author_email = myemail@example.com

    """
    def __init__(self):
        parser = ConfigParser()
        parser.read(os.path.expanduser('~/.pypirc'))
        self.author = parser.get('simple_setup', 'author', fallback=None)
        self.author_email = parser.get('simple_setup', 'author_email', fallback=None)

class GitConfig:
    """
    ~/.gitconfig

    [user]
            name = My Name Is
            email = myemail@example.com

    """
    def __init__(self):
        parser = ConfigParser()
        parser.read(os.path.expanduser('~/.gitconfig'))
        self.author = parser.get('user', 'name', fallback=None)
        self.author_email = parser.get('user', 'email', fallback=None)

class HgRc:
    """
    ~/.hgrc
    [ui]
    username = My Name Is <myemail@example.com>
    """
    def __init__(self):
        parser = ConfigParser()
        parser.read(os.path.expanduser('~/.hgrc'))
        username = parser.get('ui', 'username', fallback=None)
        name_email = getaddresses([username])
        self.author = None
        self.author_email = None
        if name_email:
            self.author = name_email[0][0]
            self.author_email = name_email[0][1]


class DotGitConfig:
    """Grab info out of a .git/config file.

    [remote "origin"]
        url = git@github.com:pygame/solarwolf.git

    """
    def __init__(self):
        """
        """


def read(*parts):
    """Reads in file from *parts.
    """
    try:
        return io.open(os.path.join(*parts), 'r', encoding='utf-8').read()
    except IOError:
        return ''

def version_from_file(fname):
    """
    """
    version_file = read(fname)
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                              version_file, re.MULTILINE)
    if version_match:
        return version_match.group(1)


def version_from_git():
    """Gets the current version from git tags.
    """
    try:
        versions = subprocess.check_output('git tag --sort version:refname'.split())
    except subprocess.CalledProcessError:
        return
    lines = versions.splitlines()
    if lines:
        return lines[-1].decode('utf-8')

# find('*.py', 'some/path/')
# def find(pattern, path):
#     result = []
#     for root, _, files in os.walk(path):
#         for name in files:
#             if fnmatch(name, pattern):
#                 result.append(os.path.join(root, name))
#     return result


def package_py(what_to_package):
    """Is there a .py file for this repo or a __init__.py ?

    package_py('.')
    package_py('mypackage.py')
    package_py('/Users/bla/packagefolder/')

    This detects single file packages, and packages with __init__.py in them.
    """
    if what_to_package.endswith('.py'):
        return what_to_package

    if os.path.isdir(what_to_package) or what_to_package == '.':
        # lets see if there is a __init__.py in there.
        apath = os.path.join(what_to_package, '__init__.py')
        if os.path.exists(apath):
            return apath

        # maybe there is a file with the same name as the folder?
        folder_name = os.path.split(os.path.abspath(what_to_package))[-1]
        apath = os.path.join(what_to_package, folder_name + '.py')
        if os.path.exists(apath):
            return apath

        apath = os.path.join(what_to_package, folder_name, '__init__.py')
        if os.path.exists(apath):
            return apath



def dependencies_ast(apy):
    """Try to find 3rd party dependencies in the past in .py file.

    Returns a list of package names.
    """
    module = ast.parse(open(apy).read())
    deps = []
    for node in module.body:
        if type(node) is ast.Import:
            for name in node.names:
                parts = imp.find_module(name.name.split('.')[0])
                if 'site-package' in parts[1]:
                    deps.append(name.name.split('.')[0])
        if type(node) is ast.ImportFrom:

            parts = imp.find_module(node.module.split('.')[0])
            if 'site-package' in parts[1]:
                deps.append(node.module.split('.')[0])

    return deps



class ModuleDocs:
    """For getting the description and long_description out of the module docstring
    """
    def __init__(self, what_to_package):
        data = read(package_py(what_to_package))
        lines = ast.parse(data).body[0].value.s.splitlines()
        self.description = lines[0]
        self.long_description = '\n'.join(lines)


class GatherInfo:

    def __init__(self, what_to_package):
        """
        :param folder_to_package: this is the folder or file we want to package.
                                  It could be
        """
        self.what_to_package = what_to_package
        self.pypirc = PyPiRc()
        self.gitconfig = GitConfig()
        self.hgrc = HgRc()
        self.module_docs = ModuleDocs(what_to_package)

    @property
    def author(self):
        if self.pypirc.author is not None:
            return self.pypirc.author
        if self.gitconfig.author is not None:
            return self.gitconfig.author

    @property
    def author_email(self):
        if self.pypirc.author_email is not None:
            return self.pypirc.author_email
        if self.gitconfig.author_email is not None:
            return self.gitconfig.author_email

    @property
    def name(self):
        """ We can get this by looking at what is there.

        Is there a single python file? 'leftpad.py' -> 'leftpad'
        Is there a single folder of python files? 'leftpad/' -> 'leftpad'
        If it is '.' then we use the folder name -> 'leftpad'
        """
        if self.what_to_package.endswith('.py'):
            return self.what_to_package.rstrip('.py')

        if os.path.isdir(self.what_to_package):
            return os.path.split(os.path.abspath(self.what_to_package))[-1]


    @property
    def description(self):
        return self.module_docs.description

    @property
    def long_description(self):
        return self.module_docs.long_description

    @property
    def version(self):
        afile = package_py(self.what_to_package)
        print(afile)
        ver = version_from_file(afile)
        if ver is None:
            ver = version_from_git()
        if ver is None:
            ver = '0.0.0'
        return ver


    @property
    def url(self):
        # from .git/config
        if os.path.isdir(self.what_to_package):
            package_name = os.path.split(os.path.abspath(self.what_to_package))[-1]
            return 'https://pypi.python.org/pypi/%s' % package_name

    @property
    def install_requires(self):
        if self.what_to_package.endswith('.py'):
            return dependencies_ast(self.what_to_package)
        else:
            return []

    def is_data_files(self):
        return False

    @property
    def is_script(self):
        """Is the package a script? Does it have a module.main() ?
        """
        return 'def main' in read(package_py(self.what_to_package))

    @property
    def is_single_file(self):
        return package_py(self.what_to_package)



    def __str__(self):
        """
        """
        output = """
name="{name}"
description = {description}
long_description = {long_description}
author_email="{author_email}"
author="{author}"
version="{version}"
url="{url}"
is_script={is_script}
"""
        return output.format(name=self.name,
                             description=repr(self.description),
                             long_description=repr(self.long_description),
                             author_email=self.author_email,
                             author=self.author,
                             version=self.version,
                             url=self.url,
                             is_script=self.is_script)


SETUP_PY = """
from setuptools import setup, find_packages
setup(
    name='{name}',
    version='{version}',
    description={description},
    long_description={long_description},
    url='{url}',
    author='{author}',
    author_email='{author_email}',
    license='{license}',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    {packages}
    {py_modules}
    {install_requires}
    {console_scripts}
)
"""

MANIFEST_IN = """

# Include the license file
# include LICENSE.txt

# Include the data files
{include_data_files}
"""


class FillFiles:
    """ This fills setup files in with what they need.
    """

    def __init__(self, package_info):
        self.package_info = package_info
        self.tmpdir = tempfile.mkdtemp()
        print (self.tmpdir)
        # repo = 'https://github.com/pypa/sampleproject/'
        # subprocess.check_output = 'git clone %s %s' % (repo, self.tmpdir)

        setup_py_data = self.setup_py()
        manifest_in_data = self.manifest_in()

        with open(os.path.join(self.tmpdir, 'setup.py'), 'w') as afile:
            afile.write(setup_py_data)
        with open(os.path.join(self.tmpdir, 'MANIFEST.in'), 'w') as afile:
            afile.write(manifest_in_data)

        self.copy_files()


    def copy_files(self):
        """Copies our package files into the new output folder.
        """
        if self.package_info.is_single_file:
            pyfname = package_py(self.package_info.what_to_package)
            dstpath = os.path.join(self.tmpdir, pyfname)
            copyfile(pyfname, dstpath)
        else:
            raise NotImplementedError('only single files supported')


    def manifest_in(self):
        """Fill in a MANIFEST.in
        """
        include_data_files = 'recursive-include data *' if self.package_info.is_data_files else ''
        return MANIFEST_IN.format(include_data_files=include_data_files)

    def setup_py(self):
        """Fill in a setup.py string.
        """

        if self.package_info.is_script:
            console_scripts = """
            entry_points={
                'console_scripts': [
                    '%s=%s:main',
                ],
            },
            """ % (self.package_info.name, self.package_info.name)
        else:
            console_scripts = ''

        if self.package_info.is_single_file:
            py_modules = "py_modules=['%s']," % self.package_info.name
            packages = ''
        else:
            raise NotImplementedError('only single files supported')
            py_modules = ''
            packages = "packages=find_packages(exclude=['contrib', 'docs', 'tests']),"


        install_requires = "install_requires=%s," % repr(self.package_info.install_requires)

        return SETUP_PY.format(name=self.package_info.name,
                               description=repr(self.package_info.description),
                               long_description=repr(self.package_info.long_description),
                               author_email=self.package_info.author_email,
                               author=self.package_info.author,
                               version=self.package_info.version,
                               url=self.package_info.url,
                               console_scripts=console_scripts,
                               install_requires=install_requires,
                               license='MIT',
                               packages=packages,
                               py_modules=py_modules)


class UploadPyPi:
    """
    """
    # twine upload dist/*.tar.gz
    def build(self):
        # python setup.py build sdist bdist_wheel
        pass
    def upload(self):
        pass
        # python setup.py upload


def main():
    """
    """
    package_info = GatherInfo('.')
    filled_files = FillFiles(package_info)


if __name__ == '__main__':
    main()
    # print(GatherInfo('.'))
