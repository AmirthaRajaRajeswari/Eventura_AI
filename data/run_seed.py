"""Quick runner for the seed — avoids __name__ guard issues."""
import sys, traceback
sys.path.insert(0, '.')
try:
    from seed import main
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
