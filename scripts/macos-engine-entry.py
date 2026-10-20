"""Native macOS engine entry; keep Qt out of inference processes."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    import haizflow.config  # noqa: F401
    from haizflow.engine.main import main

    raise SystemExit(main())
