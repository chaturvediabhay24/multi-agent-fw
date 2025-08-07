#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv

from agents.agent_registry import AgentRegistry
from agents.custom_agent import CustomAgent
from conversations.conversation_manager import ConversationManager

# Load environment variables
load_dotenv()


def interactive_mode(agent):
    """Interactive terminal mode for continuous conversation"""
    print(f"\n🤖 Starting interactive session with {agent.name}")
    print(f"📝 Conversation ID: {agent.conversation_id}")
    print(f"🔧 Model: {agent.config.get('model_type', 'unknown')} - {agent.config.get('model_name', 'unknown')}")
    print("\nType 'quit', 'exit', or 'bye' to end the conversation")
    print("Type '/help' for commands")
    print("=" * 50)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n🧑 You: ").strip()
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"\n👋 Goodbye! Conversation saved as: {agent.conversation_id}")
                break
            
            if user_input == '/help':
                print("\nAvailable commands:")
                print("  /help - Show this help")
                print("  /info - Show agent info")
                print("  /debug - Toggle debug mode")
                print("  /tools - Show tool call history")
                print("  /switch <model_type> <model_name> - Switch model")
                print("  /history - Show conversation history")
                print("  quit/exit/bye - End conversation")
                continue
            
            if user_input == '/info':
                print(f"\nAgent: {agent.name}")
                print(f"Description: {agent.get_description()}")
                print(f"Model: {agent.config.get('model_type')} - {agent.config.get('model_name')}")
                print(f"Tools: {', '.join(agent.get_available_tools()) or 'None'}")
                
                # Show debug info if agent supports it
                if hasattr(agent, 'get_debug_info'):
                    debug_info = agent.get_debug_info()
                    print(f"Debug Mode: {'ON' if debug_info['debug_mode'] else 'OFF'}")
                    print(f"Tool Calls Made: {debug_info['tool_calls_in_session']}")
                continue
            
            if user_input == '/debug':
                if hasattr(agent, 'debug_mode'):
                    if agent.debug_mode:
                        agent.disable_debug()
                        print("🔧 Debug mode OFF")
                    else:
                        agent.enable_debug()
                        print("🔧 Debug mode ON")
                else:
                    print("❌ Debug mode not supported by this agent")
                continue
            
            if user_input == '/tools':
                if hasattr(agent, 'get_tool_call_history'):
                    tool_history = agent.get_tool_call_history()
                    if tool_history:
                        print(f"\nTool Call History ({len(tool_history)} calls):")
                        for i, call in enumerate(tool_history, 1):
                            status = "✅" if call['success'] else "❌"
                            print(f"  {i}. {status} {call['tool_name']}({call['params']})")
                            if not call['success']:
                                print(f"     Error: {call['result']}")
                    else:
                        print("\nNo tool calls made yet in this session")
                else:
                    print("❌ Tool history not supported by this agent")
                continue
            
            if user_input.startswith('/switch'):
                parts = user_input.split()
                if len(parts) == 3:
                    model_type, model_name = parts[1], parts[2]
                    try:
                        agent.switch_model(model_type, model_name)
                        print(f"✅ Switched to {model_type} - {model_name}")
                    except Exception as e:
                        print(f"❌ Error switching model: {e}")
                else:
                    print("Usage: /switch <model_type> <model_name>")
                    print("Example: /switch claude claude-3-sonnet-20240229")
                continue
            
            if user_input == '/history':
                print(f"\nConversation History ({len(agent.conversation_history)} messages):")
                for i, msg in enumerate(agent.conversation_history):
                    msg_type = msg.__class__.__name__.replace('Message', '')
                    content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    
                    # Check if this is an AI message with tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls_str = ", ".join([call['name'] for call in msg.tool_calls])
                        print(f"  {i+1}. {msg_type}: {content}")
                        print(f"      🔧 Tool calls: {tool_calls_str}")
                    else:
                        print(f"  {i+1}. {msg_type}: {content}")
                continue
            
            if not user_input:
                continue
            
            # Send message to agent
            print(f"\n🤖 {agent.name}: ", end="", flush=True)
            response = agent.invoke(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Conversation interrupted. Saved as: {agent.conversation_id}")
            break
        except EOFError:
            print(f"\n\n👋 Input stream ended. Conversation saved as: {agent.conversation_id}")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Multi-Agent Framework')
    parser.add_argument('--agent', '-a', help='Agent name to run')
    parser.add_argument('--message', '-m', help='Message to send to agent (for single message mode)')
    parser.add_argument('--conversation-id', '-c', help='Existing conversation ID to continue')
    parser.add_argument('--model-type', help='Override model type (openai/claude)')
    parser.add_argument('--model-name', help='Override model name')
    parser.add_argument('--interactive', '-i', action='store_true', help='Start interactive mode')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--list-agents', action='store_true', help='List all available agents')
    parser.add_argument('--list-conversations', action='store_true', help='List all conversations')
    parser.add_argument('--conversation-summary', action='store_true', help='Show conversation statistics')
    parser.add_argument('--organize-conversations', action='store_true', help='Organize conversations by date')
    parser.add_argument('--agent-conversations', help='List conversations for specific agent')
    
    args = parser.parse_args()
    
    # Initialize registry and load agents
    registry = AgentRegistry()
    registry.load_agents_from_config()
    
    if args.list_agents:
        agents = registry.list_agents()
        print("Available agents:")
        for name, description in agents.items():
            print(f"  {name}: {description}")
        return
    
    if args.list_conversations:
        conv_manager = ConversationManager()
        conversations = conv_manager.list_conversations()
        print("Available conversations:")
        for conv in conversations:
            agent_name = conv.get('metadata', {}).get('agent_name', 'unknown')
            print(f"  {conv['conversation_id']}: {conv['timestamp']} ({conv['message_count']} messages) - Agent: {agent_name}")
        return
    
    if args.conversation_summary:
        conv_manager = ConversationManager()
        summary = conv_manager.get_conversation_summary()
        print("📊 Conversation Summary:")
        print(f"  Total conversations: {summary['total_conversations']}")
        print(f"  Total messages: {summary['total_messages']}")
        print(f"  Agents used: {', '.join(summary['agents_used']) if summary['agents_used'] else 'None'}")
        print(f"  Models used: {', '.join(summary['models_used']) if summary['models_used'] else 'None'}")
        if summary['date_range']['earliest']:
            print(f"  Date range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
        return
    
    if args.organize_conversations:
        conv_manager = ConversationManager()
        organized = conv_manager.organize_conversations_by_date()
        print(f"📅 Organized {organized} conversations by date")
        return
    
    if args.agent_conversations:
        conv_manager = ConversationManager()
        conversations = conv_manager.get_conversations_by_agent(args.agent_conversations)
        print(f"Conversations for agent '{args.agent_conversations}':")
        for conv in conversations:
            print(f"  {conv['conversation_id']}: {conv['timestamp']} ({conv['message_count']} messages)")
        return
    
    # Check if we need an agent for the operation
    if not args.list_agents and not args.list_conversations:
        if not args.agent:
            print("Error: --agent is required unless using --list-agents or --list-conversations")
            print("Use --help for usage information")
            sys.exit(1)
        
        # Get or create agent
        agent = registry.get_agent(args.agent)
        if not agent:
            print(f"Agent '{args.agent}' not found. Creating custom agent.")
            config = {
                'model_type': args.model_type or 'openai',
                'model_name': args.model_name or 'gpt-3.5-turbo',
                'description': f'Custom agent: {args.agent}'
            }
            agent = CustomAgent(args.agent, config, args.conversation_id)
            registry.register_agent(args.agent, agent)
        else:
            # Override model if specified
            if args.model_type or args.model_name:
                agent.switch_model(
                    args.model_type or agent.config.get('model_type', 'openai'),
                    args.model_name or agent.config.get('model_name', 'gpt-3.5-turbo')
                )
            
            # Set conversation ID if provided
            if args.conversation_id:
                agent.conversation_id = args.conversation_id
                agent.conversation_history = agent.conversation_manager.load_conversation(args.conversation_id)
        
        # Enable debug mode if requested
        if args.debug and hasattr(agent, 'enable_debug'):
            agent.enable_debug()
            print("🔧 Debug mode enabled")
        
        # Decide between interactive mode and single message mode
        if args.interactive or not args.message:
            # Interactive mode
            interactive_mode(agent)
        else:
            # Single message mode
            try:
                response = agent.invoke(args.message)
                print(f"\n{agent.name}: {response}")
                print(f"\nConversation ID: {agent.conversation_id}")
                
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)


if __name__ == "__main__":
    main()