class DummyConnectionManager:
    def list_actions(self, connection_name):
        print(f"Available actions for connection '{connection_name}'")

    def configure_connection(self, connection_name):
        print(f"Configuring connection '{connection_name}'")

    def list_connections(self):
        print("Available connections: example_connection")

class ZerePyAgent:
    def __init__(self, agent_name):
        self.name = agent_name
        self.is_llm_set = True  # Set to False to test setup prompt
        self.connection_manager = DummyConnectionManager()

    def perform_action(self, connection, action, params):
        return f"Performed action '{action}' on connection '{connection}' with params {params}"

    def loop(self):
        print("Running agent loop... (Ctrl+C to stop)")

    def _setup_llm_provider(self):
        print("Setting up LLM provider...")

    def prompt_llm(self, prompt):
        return f"LLM response to: {prompt}"
