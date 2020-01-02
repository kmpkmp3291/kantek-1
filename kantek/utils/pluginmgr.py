"""Contains the Plugin Manager handling loading and unloading of plugins."""
import ast
import importlib.util
import os
from dataclasses import dataclass
from importlib._bootstrap import ModuleSpec
from importlib._bootstrap_external import SourceFileLoader
from logging import Logger
from typing import Callable, Dict, List, Tuple

import logzero
from telethon import TelegramClient, events

logger: Logger = logzero.logger

__version__ = '0.1.0'


class KantekPlugin:
    name = None
    help = None


@dataclass
class Callback:
    """A Plugin callback

    Attributes:
        name: Callback name
        help: Callback help
        callback: The callback function
        private: If the callback is private or not
    """
    name: str
    help: str
    callback: Callable
    private: bool


@dataclass
class Plugin:
    """A Plugin with callbacks.

    Attributes:
        name: Plugin name without path
        help: Help on how to use the plugin
        callbacks: List of callbacks the plugin has
        full_path: Absolute path to the plugin
        plugin_path: Plugin folder the plugin lies in
        path: Plugin Path relative to the Plugin Folder
        version: The plugin version
    """
    name: str
    help: str
    callbacks: List[Callback]
    full_path: str
    plugin_path: str
    version: str

    @property
    def path(self) -> str:
        """Return the plugin path relative to the plugin folder."""
        return (os.path.relpath(self.full_path, self.plugin_path)
                .rstrip('.py')
                # replace the backslash in windows paths
                .replace('\\', '/'))


class PluginManager:
    """Mange loading and unloading of plugins."""
    active_plugins: List[Plugin] = []

    def __init__(self, client: TelegramClient) -> None:
        self.client = client
        self.plugin_path: str = os.path.abspath('./plugins')

    def register_all(self) -> List[Plugin]:
        """Get a list of all plugins and register them with the client.

        Returns: List of active plugins

        """
        for plugin_name, path in self._get_plugin_list():
            plugin_info = self._get_plugin_info(plugin_name, path)
            active_commands = []
            for callback in self._get_plugin_callbacks(plugin_name, path):
                logger.debug('Registered plugin %s/%s',
                             self._get_plugin_location(path), callback.name)
                active_commands.append(callback)
                self.client.add_event_handler(callback.callback)
            self.active_plugins.append(
                Plugin(plugin_name,
                       plugin_info['help'],
                       active_commands,
                       path,
                       self.plugin_path,
                       plugin_info['version']))

        logger.info('Registered %s plugins.', len(self.active_plugins))
        return self.active_plugins

    def unregister_all(self, builtins: bool = False) -> None:
        """Unregister all plugins

        Args:
            builtins: Flag if builtin plugins should be removed too.

        Returns: None
        """
        for plugin in self.active_plugins:
            if builtins:
                self.unregister_plugin(plugin)
            else:
                if not plugin.path.startswith('builtins/'):
                    self.unregister_plugin(plugin)

    def unregister_plugin(self, plugin: Plugin) -> None:
        """Unregister a specific plugin.

        Args:
            plugin: The plugin to unregister

        Returns: None

        """
        for callback in plugin.callbacks:
            logger.debug(self.client.remove_event_handler(callback.callback))
        self.active_plugins.remove(plugin)

    def _get_plugin_location(self, path: str) -> str:
        return (os.path.relpath(path, self.plugin_path)
                .rstrip('.py')
                # replace the backslash in windows paths
                .replace('\\', '/'))

    def _get_plugin_list(self) -> List[Tuple[str, str]]:
        plugins: List[Tuple[str, str]] = []
        for root, dirs, files in os.walk(self.plugin_path):  # pylint: disable = W0612
            for file in files:
                path = os.path.join(root, file)
                name, ext = os.path.splitext(file)
                if ext == '.py':
                    plugins.append((name, path))
        return plugins

    def _get_plugin_callbacks(self, name: str, path: str) -> List[Callback]:
        _module: ModuleSpec = importlib.util.spec_from_file_location(name, path)
        loader: SourceFileLoader = _module.loader
        module = loader.load_module()
        callbacks = []
        with open(path, encoding='utf-8') as f:
            tree = ast.parse(f.read())
            for item in tree.body:
                if isinstance(item, ast.ClassDef) and not item.name.startswith('_') and item.bases:
                    plugin = getattr(module, item.name)
                    if issubclass(plugin, KantekPlugin):
                        for method in item.body:
                            if isinstance(method, ast.AsyncFunctionDef):
                                func = getattr(plugin, method.name)
                                if events.is_handler(func):
                                    is_private = self.__is_private(
                                        self.__get_event_decorator_keywords(method))
                                    callbacks.append(
                                        Callback(method.name, func.__doc__, func, is_private))
        return callbacks

    @staticmethod
    def _get_plugin_info(name: str, path: str) -> Dict:
        _module: ModuleSpec = importlib.util.spec_from_file_location(name, path)
        loader: SourceFileLoader = _module.loader
        module = loader.load_module()
        version = ''
        name = ''
        plugin_help = ''
        with open(path, encoding='utf-8') as f:
            tree = ast.parse(f.read())
            for item in tree.body:
                if isinstance(item, ast.Assign):
                    target = item.targets[0]
                    if target.id == '__version__':
                        version = item.value.s
                elif isinstance(item, ast.ClassDef) and not item.name.startswith('_') and item.bases:
                    plugin = getattr(module, item.name)
                    if issubclass(plugin, KantekPlugin):
                        name = plugin.name
                        plugin_help = plugin.help
        return {'version': version, 'name': name, 'help': plugin_help}

    @staticmethod
    def __is_private(keywords: Dict[str, bool]) -> bool:
        incoming = keywords.get('incoming')
        outgoing = keywords.get('outgoing')
        is_private = False
        if incoming is not None:
            is_private = not incoming
        if outgoing is not None:
            is_private = outgoing
        return is_private

    @classmethod
    def __get_event_decorator_keywords(cls, func: ast.AsyncFunctionDef) -> Dict[str, bool]:
        keywords = {}
        for decorator in func.decorator_list:
            if decorator.func.value.id == 'events':
                keywords.update(cls.__get_keywords(decorator))
        return keywords

    @staticmethod
    def __get_keywords(decorator: ast.Call) -> Dict[str, bool]:
        keywords = {}
        for arg in decorator.args:
            for keyword in arg.keywords:
                value = keyword.value
                if isinstance(value, ast.NameConstant):
                    keywords.update({keyword.arg: value.value})
        return keywords
