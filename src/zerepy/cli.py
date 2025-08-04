import sys
import json
import logging
import os
import shlex
from dataclasses import dataclass
from typing import Callable, Dict, List
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from zerepy.agent import ZerePyAgent


def print_h_bar():
    print("-" * 60)


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("cli")


@dataclass
class Command:
    name: str
    description: str
    tips: List[str]
    handler: Callable
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class ZerePyCLI:
    def __init__(self):
        self.agent = None
        self.config_dir = Path.home() / '.zerepy'
        self.config_dir.mkdir(exist_ok=True)
        self._initialize_commands()
        self._setup_prompt_toolkit()

    def _initialize_commands(self):
        self.commands: Dict[str, Command] = {}
        self._register_command(Command("help", "Show help", ["help", "help load-agent"], self.help, ["h", "?"]))
        self._register_command(Command("clear", "Clear the screen", ["clear"], self.clear_screen, ["cls"]))
        self._register_command(Command("agent-action", "Run agent action", ["agent-action conn action"], self.agent_action, ["action", "run"]))
        self._register_command(Command("agent-loop", "Run agent loop", ["start"], self.agent_loop, ["loop", "start"]))
        self._register_command(Command("list-agents", "List agent files", [], self.list_agents, ["agents", "ls-agents"]))
        self._register_command(Command("load-agent", "Load an agent", ["load-agent agent_name"], self.load_agent, ["load"]))
        self._register_command(Command("create-agent", "Create new agent", [], self.create_agent, ["new-agent", "create"]))
        self._register_command(Command("set-default-agent", "Set default agent", ["default agent_name"], self.set_default_agent, ["default"]))
        self._register_command(Command("chat", "Chat with agent", [], self.chat_session, ["talk"]))
        self._register_command(Command("list-actions", "List actions for connection", ["list-actions conn"], self.list_actions, ["actions", "ls-actions"]))
        self._register_command(Command("configure-connection", "Configure a connection", ["configure-connection conn"], self.configure_connection, ["config", "setup"]))
        self._register_command(Command("list-connections", "List all connections", [], self.list_connections, ["connections", "ls-connections"]))
        self._register_command(Command("exit", "Exit CLI", ["exit"], self.exit, ["quit", "q"]))

    def _setup_prompt_toolkit(self):
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            'command': 'ansigreen',
            'error': 'ansired bold',
            'success': 'ansigreen bold',
            'warning': 'ansiyellow',
        })
        history_file = self.config_dir / 'history.txt'
        self.completer = WordCompleter(list(self.commands.keys()), ignore_case=True, sentence=True)
        self.session = PromptSession(completer=self.completer, style=self.style, history=FileHistory(str(history_file)))

    def _register_command(self, command: Command):
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command

    def _get_prompt_message(self):
        agent_status = f"({self.agent.name})" if self.agent else "(no agent)"
        return HTML(f'<prompt>ZerePy-CLI</prompt> {agent_status} > ')

    def _handle_command(self, input_string: str):
        try:
            input_list = shlex.split(input_string)
            if not input_list:
                return
            command_string = input_list[0].lower()
            command = self.commands.get(command_string)
            if command:
                command.handler(input_list)
            else:
                self._handle_unknown_command(command_string)
        except Exception as e:
            logger.error(f"Error: {e}")

    def _handle_unknown_command(self, command: str):
        logger.warning(f"Unknown command: '{command}'")
        suggestions = self._get_command_suggestions(command)
        if suggestions:
            logger.info("Did you mean?")
            for s in suggestions:
                logger.info(f"  - {s}")
        logger.info("Use 'help' to see all commands.")

    def _get_command_suggestions(self, command: str, max_suggestions: int = 3):
        from difflib import get_close_matches
        return get_close_matches(command, self.commands.keys(), n=max_suggestions, cutoff=0.6)

    def _print_welcome_message(self):
        print_h_bar()
        logger.info("👋 Welcome to the ZerePy CLI!")
        logger.info("Type 'help' to list commands.")
        print_h_bar()

    def _load_default_agent(self):
        try:
            with open(Path("agents") / "general.json", "r") as f:
                data = json.load(f)
            default_agent = data.get("default_agent")
            if default_agent:
                self._load_agent_from_file(default_agent)
            else:
                logger.warning("No default agent set.")
        except Exception as e:
            logger.warning(f"Failed to load default agent: {e}")

    def _load_agent_from_file(self, agent_name):
        try:
            self.agent = ZerePyAgent(agent_name)
            logger.info(f"✅ Loaded agent: {self.agent.name}")
        except Exception as e:
            logger.error(f"Could not load agent: {e}")

    def help(self, input_list: List[str]):
        if len(input_list) > 1:
            cmd = self.commands.get(input_list[1])
            if cmd:
                logger.info(f"{cmd.name}: {cmd.description}")
                for tip in cmd.tips:
                    logger.info(f"  - {tip}")
            else:
                logger.warning("Command not found.")
        else:
            logger.info("Commands:")
            seen = set()
            for cmd in self.commands.values():
                if cmd.name not in seen:
                    logger.info(f"  {cmd.name:<20} - {cmd.description}")
                    seen.add(cmd.name)

    def clear_screen(self, input_list: List[str]):
        os.system("cls" if os.name == "nt" else "clear")
        self._print_welcome_message()

    def agent_action(self, input_list: List[str]):
        if not self.agent:
            logger.info("No agent loaded.")
            return
        if len(input_list) < 3:
            logger.info("Usage: agent-action <connection> <action>")
            return
        result = self.agent.perform_action(input_list[1], input_list[2], input_list[3:])
        logger.info(f"Result: {result}")

    def agent_loop(self, input_list: List[str]):
        if not self.agent:
            logger.info("No agent loaded.")
            return
        try:
            self.agent.loop()
        except KeyboardInterrupt:
            logger.info("Stopped.")

    def list_agents(self, input_list: List[str]):
        agents = list(Path("agents").glob("*.json"))
        for agent_file in agents:
            if agent_file.stem != "general":
                logger.info(f"- {agent_file.stem}")

    def load_agent(self, input_list: List[str]):
        if len(input_list) < 2:
            logger.info("Usage: load-agent <agent_name>")
            return
        self._load_agent_from_file(input_list[1])

    def create_agent(self, input_list: List[str]):
        logger.info("Manual creation: add a .json file in agents/ folder.")

    def set_default_agent(self, input_list: List[str]):
        if len(input_list) < 2:
            logger.info("Usage: set-default-agent <agent_name>")
            return
        try:
            path = Path("agents") / "general.json"
            with open(path, "r") as f:
                data = json.load(f)
            data["default_agent"] = input_list[1]
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            logger.info(f"Default agent set to {input_list[1]}")
        except Exception as e:
            logger.error(f"Error updating default agent: {e}")

    def list_actions(self, input_list: List[str]):
        if not self.agent:
            logger.info("No agent loaded.")
            return
        if len(input_list) < 2:
            logger.info("Usage: list-actions <connection>")
            return
        self.agent.connection_manager.list_actions(input_list[1])

    def configure_connection(self, input_list: List[str]):
        if not self.agent:
            logger.info("No agent loaded.")
            return
        if len(input_list) < 2:
            logger.info("Usage: configure-connection <connection>")
            return
        self.agent.connection_manager.configure_connection(input_list[1])

    def list_connections(self, input_list: List[str]):
        if self.agent:
            self.agent.connection_manager.list_connections()
        else:
            logger.info("No agent loaded.")

    def chat_session(self, input_list: List[str]):
        if not self.agent:
            logger.info("Load an agent first.")
            return
        if not self.agent.is_llm_set:
            self.agent._setup_llm_provider()
        print_h_bar()
        logger.info(f"Chatting with {self.agent.name}")
        print_h_bar()
        while True:
            try:
                message = self.session.prompt("\nYou: ")
                if message.strip().lower() == "exit":
                    break
                response = self.agent.prompt_llm(message)
                logger.info(f"{self.agent.name}: {response}")
                print_h_bar()
            except KeyboardInterrupt:
                break

    def exit(self, input_list: List[str]):
        logger.info("Goodbye!")
        sys.exit(0)

    def main_loop(self):
        self._print_welcome_message()
        self._load_default_agent()
        while True:
            try:
                user_input = self.session.prompt(self._get_prompt_message(), style=self.style)
                if user_input.strip():
                    self._handle_command(user_input.strip())
                    print_h_bar()
            except KeyboardInterrupt:
                continue
            except EOFError:
                self.exit([])


def main():
    cli = ZerePyCLI()
    cli.main_loop()
if __name__ == "__main__":
    main()
