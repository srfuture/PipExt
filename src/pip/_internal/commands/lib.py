import os
from pip._internal.cli.base_command import Command
import zipfile
import ast
import importlib.metadata
import subprocess

def add_tmp_to_lib():
    tmp_path = "./tmp"
    lib_file = "./packages.lib"
  
    with zipfile.ZipFile(lib_file, 'a') as libf:
        for root, dirs, files in os.walk(tmp_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = file_path.replace(tmp_path, '')
                libf.write(file_path, arcname)
        # Remove the temp directory after adding files
        for root, dirs, files in os.walk(tmp_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(tmp_path)

def get_imported_modules_with_versions(directory):
    imported_modules = set()
    module_versions = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                                for alias in node.names:
                                    # Get the top-level module name
                                    module_name = alias.name.split('.')[0]
                                    # Validate module name
                                    if module_name and module_name.isidentifier():
                                        imported_modules.add(module_name)
                    except SyntaxError as e:
                        print(f"SyntaxError in {file_path}: {e}")

    for module in imported_modules:
        try:
            version = importlib.metadata.version(module)
            module_versions[module] = version
        except importlib.metadata.PackageNotFoundError:
            # If the version is not found, add the module with no version
            module_versions[module] = None

    return module_versions

def create_empty_lib():
    lib_file = "packages.lib"
    if os.path.exists(lib_file):
        print(f"File '{lib_file}' already exists.")
        return

    with zipfile.ZipFile(lib_file, 'w') as myzip:
        print(
            """
            Succeeded in creating `packages.lib`

            Please compress all libraries of the project using `pip lib tidy`
            """
        )

class LibCommand(Command):
    name = 'lib'
    usage = """
        %prog [options] <subcommand> [args]
    """
    summary = 'Used to create lib zip'

    def __init__(self, *args, **kwargs):
        super(LibCommand, self).__init__(*args, **kwargs)

    def run(self, options, args):
        if not args:
            print("Please provide a subcommand: init, tidy, install")
            return 1  # 返回非零状态码表示失败

        subcommand = args[0]

        if subcommand == 'init':
            self.init_lib()
            return 0  # 成功返回0
        elif subcommand == 'tidy':
            self.tidy_lib()
            return 0
        elif subcommand == 'install':
            if len(args) > 1:
                self.install_lib(args[1])
                return 0
            else:
                print("Please provide a path to install")
                return 1
        else:
            print(f"Unknown subcommand {subcommand}. Available subcommands are: init, tidy, install")
            return 1

    def init_lib(self):
        create_empty_lib()

    def tidy_lib(self):
        if os.path.exists("./packages.lib"):
            module_versions = get_imported_modules_with_versions(".")

            for module, version in module_versions.items():
                try:
                    if version:
                        # Download the wheel format specifically
                        subprocess.check_call([os.sys.executable, '-m', 'pip', 'download', f"{module}=={version}", '-d', './tmp', '--only-binary', ':all:'])
                    else:
                        subprocess.check_call([os.sys.executable, '-m', 'pip', 'download', module, '-d', './tmp', '--only-binary', ':all:'])
                except subprocess.CalledProcessError as e:
                    print(f"Skipping {module} due to error: {e}")
            add_tmp_to_lib()
        else:
            print("Please create the lib file with pip lib init")

    def install_lib(self, path):
        with zipfile.ZipFile(path, 'r') as lib_ref:
            # 列出文件
            # lib_ref.printdir()

            # 解压到指定目录
            lib_ref.extractall('./tmp')
            lib_ref.close()
        for file in os.listdir('./tmp'):
            os.system(f'pip install ./tmp/{file}')
        os.rmdir("./tmp")
