# AppLimiter/src/applimiter/main.py
import sys

from applimiter import cli, daemon

def main():
    try:
        cli.setup_logging()
        args = cli.parse_arguments()

        if args.command == "daemon":
            daemon.run_daemon(check_interval=args.interval)
        else:
            cli.handle_cli_command(args)

    except Exception as e:
        print(f"A fatal error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()