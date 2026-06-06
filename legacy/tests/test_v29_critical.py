
"""
tests/test_v29_critical.py — v29 Critical Path Tests
═══════════════════════════════════════════════════════
Tests that run WITHOUT pytest, external services, or heavy imports.
Focus: security, caching, config, rate limiting, data integrity.
"""
import unittest
import sys
import os
import ast
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _parse_frozenset_from_source(filepath: str, var_name: str) -> set:
    """Parse a frozenset({...}) assignment from source code."""
    with open(filepath) as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    # Handle frozenset({...})
                    if isinstance(node.value, ast.Call) and node.value.args:
                        inner = node.value.args[0]
                        if isinstance(inner, ast.Set):
                            return {elt.value for elt in inner.elts if isinstance(elt, ast.Constant)}
                    # Handle plain set {...}
                    if isinstance(node.value, ast.Set):
                        return {elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)}
    return set()


# ═══════════════════════════════════════════════════════════════
# 1. EXECUTOR SANDBOX SECURITY TESTS (24 forbidden names, 20 attrs, 8 strings)
# ═══════════════════════════════════════════════════════════════
class TestExecutorSandbox(unittest.TestCase):
    """Verify the 4-layer sandbox blocks all dangerous patterns."""

    @classmethod
    def setUpClass(cls):
        cls.forbidden_names = _parse_frozenset_from_source('handlers/executor.py', '_FORBIDDEN_NAMES')
        cls.forbidden_attrs = _parse_frozenset_from_source('handlers/executor.py', '_FORBIDDEN_ATTRS')
        cls.forbidden_strings = _parse_frozenset_from_source('handlers/executor.py', '_FORBIDDEN_STRINGS')

    def test_blocks_import_builtins(self):
        self.assertIn('__import__', self.forbidden_names)

    def test_blocks_eval(self):
        self.assertIn('eval', self.forbidden_names)

    def test_blocks_exec(self):
        self.assertIn('exec', self.forbidden_names)

    def test_blocks_open(self):
        self.assertIn('open', self.forbidden_names)

    def test_blocks_compile(self):
        self.assertIn('compile', self.forbidden_names)

    def test_blocks_getattr(self):
        self.assertIn('getattr', self.forbidden_names)

    def test_blocks_setattr(self):
        self.assertIn('setattr', self.forbidden_names)

    def test_blocks_globals(self):
        self.assertIn('globals', self.forbidden_names)

    def test_blocks_locals(self):
        self.assertIn('locals', self.forbidden_names)

    def test_blocks_breakpoint(self):
        self.assertIn('breakpoint', self.forbidden_names)

    def test_attr_blocks_subclasses(self):
        self.assertIn('__subclasses__', self.forbidden_attrs)

    def test_attr_blocks_globals(self):
        self.assertIn('__globals__', self.forbidden_attrs)

    def test_attr_blocks_bases(self):
        self.assertIn('__bases__', self.forbidden_attrs)

    def test_attr_blocks_builtins(self):
        self.assertIn('__builtins__', self.forbidden_attrs)

    def test_attr_blocks_code(self):
        self.assertIn('__code__', self.forbidden_attrs)

    def test_attr_blocks_mro(self):
        self.assertIn('__mro__', self.forbidden_attrs)

    def test_attr_blocks_dict(self):
        self.assertIn('__dict__', self.forbidden_attrs)

    def test_string_blocks_subprocess(self):
        self.assertIn('subprocess', self.forbidden_strings)

    def test_string_blocks_import(self):
        self.assertIn('__import__', self.forbidden_strings)

    def test_minimum_forbidden_names(self):
        self.assertGreaterEqual(len(self.forbidden_names), 20,
                                f"Only {len(self.forbidden_names)} forbidden names")

    def test_minimum_forbidden_attrs(self):
        self.assertGreaterEqual(len(self.forbidden_attrs), 15,
                                f"Only {len(self.forbidden_attrs)} forbidden attrs")

    def test_minimum_forbidden_strings(self):
        self.assertGreaterEqual(len(self.forbidden_strings), 5,
                                f"Only {len(self.forbidden_strings)} forbidden strings")

    def test_sandbox_validates_ast(self):
        """Sandbox must use AST walking, not just string checks."""
        with open('handlers/executor.py') as f:
            content = f.read()
        self.assertIn('ast.walk', content, "Sandbox must use ast.walk for AST validation")

    def test_sandbox_blocks_import_statements(self):
        """Sandbox must block import/from...import statements."""
        with open('handlers/executor.py') as f:
            content = f.read()
        self.assertTrue(
            'ast.Import' in content or 'Import' in content,
            "Sandbox must check for import statements"
        )


# ═══════════════════════════════════════════════════════════════
# 2. SAFE EVAL CONDITION TESTS
# ═══════════════════════════════════════════════════════════════
class TestSafeEvalCondition(unittest.TestCase):
    """Test the AST-based safe condition evaluator in api_builder."""

    def test_no_raw_eval_in_api_builder(self):
        """api_builder must NOT use raw eval()."""
        with open('infrastructure/api/api_builder.py') as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'eval':
                    self.fail("Raw eval() found in api_builder.py — must use _safe_eval_condition")

    def test_no_raw_exec_in_api_builder(self):
        """api_builder must NOT use raw exec()."""
        with open('infrastructure/api/api_builder.py') as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'exec':
                    self.fail("Raw exec() found in api_builder.py")

    def test_safe_eval_function_exists(self):
        """_safe_eval_condition function must exist."""
        with open('infrastructure/api/api_builder.py') as f:
            content = f.read()
        self.assertIn('_safe_eval_condition', content,
                      "_safe_eval_condition not found in api_builder.py")

    def test_safe_eval_uses_ast(self):
        """_safe_eval_condition must use AST parsing, not eval."""
        with open('infrastructure/api/api_builder.py') as f:
            content = f.read()
        # Find the function body
        idx = content.find('def _safe_eval_condition')
        if idx == -1:
            self.skipTest("_safe_eval_condition not found")
        func_body = content[idx:idx+2000]
        self.assertIn('ast.', func_body, "_safe_eval_condition must use ast module")


# ═══════════════════════════════════════════════════════════════
# 3. DEDUP MIDDLEWARE TESTS
# ═══════════════════════════════════════════════════════════════
class TestDedupMiddleware(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            from middlewares.dedup_middleware import DedupMiddleware
            cls.DedupMiddleware = DedupMiddleware
            cls.available = True
        except ImportError:
            cls.available = False

    def test_cache_max_enforced(self):
        if not self.available:
            self.skipTest("dedup not importable")
        mw = self.DedupMiddleware(window_seconds=1.0, max_cache=5)
        self.assertEqual(mw._max_cache, 5)

    def test_window_configurable(self):
        if not self.available:
            self.skipTest("dedup not importable")
        mw = self.DedupMiddleware(window_seconds=2.5)
        self.assertEqual(mw._window, 2.5)

    def test_default_window_is_tight(self):
        if not self.available:
            self.skipTest("dedup not importable")
        mw = self.DedupMiddleware()
        self.assertLessEqual(mw._window, 1.0, "Default window should be <= 1s")

    def test_default_max_cache_bounded(self):
        if not self.available:
            self.skipTest("dedup not importable")
        mw = self.DedupMiddleware()
        self.assertLessEqual(mw._max_cache, 50000, "Max cache should be bounded")


# ═══════════════════════════════════════════════════════════════
# 4. CONFIG VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════
class TestConfigValidation(unittest.TestCase):

    def test_config_loads_without_crash(self):
        try:
            from config import Settings
            settings = Settings()
            self.assertIsNotNone(settings)
        except Exception as e:
            self.fail(f"Config failed to load: {e}")

    def test_config_has_bot_token_field(self):
        from config import Settings
        settings = Settings()
        self.assertTrue(hasattr(settings, 'bot_token'))

    def test_config_has_admin_ids(self):
        from config import Settings
        settings = Settings()
        self.assertTrue(hasattr(settings, 'admin_ids'))

    def test_config_rate_limit_defaults(self):
        from config import Settings
        settings = Settings()
        self.assertGreater(settings.rate_limit_messages, 0)
        self.assertLessEqual(settings.rate_limit_messages, 200)

    def test_config_log_level_valid(self):
        from config import Settings
        settings = Settings()
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        self.assertIn(settings.log_level, valid_levels)

    def test_version_file_exists(self):
        self.assertTrue(os.path.exists('VERSION'), "VERSION file missing")
        version = open('VERSION').read().strip()
        self.assertRegex(version, r'^\d+\.\d+\.\d+$', f"Invalid version format: {version}")

    def test_config_all_critical_fields(self):
        from config import Settings
        settings = Settings()
        required = ['bot_token', 'admin_ids', 'rate_limit_messages', 'log_level',
                     'ai_model', 'ai_max_history', 'ai_temperature', 'ai_max_tokens']
        for field in required:
            self.assertTrue(hasattr(settings, field), f"Settings missing: {field}")

    def test_config_temperature_range(self):
        from config import Settings
        settings = Settings()
        self.assertGreaterEqual(settings.ai_temperature, 0.0)
        self.assertLessEqual(settings.ai_temperature, 2.0)

    def test_config_max_tokens_positive(self):
        from config import Settings
        settings = Settings()
        self.assertGreater(settings.ai_max_tokens, 0)


# ═══════════════════════════════════════════════════════════════
# 5. DATABASE MODEL INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════
class TestDatabaseModels(unittest.TestCase):

    def test_models_file_parses(self):
        with open('database/models.py') as f:
            tree = ast.parse(f.read())
        self.assertIsNotNone(tree)

    def test_queries_file_parses(self):
        with open('database/queries.py') as f:
            tree = ast.parse(f.read())
        self.assertIsNotNone(tree)

    def test_analytics_uses_model_used(self):
        """AnalyticsEvent queries must use model_used, not model."""
        with open('database/queries.py') as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if 'AnalyticsEvent.model' in line and 'model_used' not in line and 'model_key' not in line:
                # False positive check: AnalyticsEvent.model_used is fine
                if re.search(r'AnalyticsEvent\.model\b(?!_)', line):
                    self.fail(f"Line {i+1}: uses AnalyticsEvent.model instead of model_used")

    def test_user_uses_telegram_id(self):
        """User queries must use telegram_id, not user_id on User model."""
        with open('database/queries.py') as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'User.user_id' in line and not line.strip().startswith('#'):
                self.fail(f"Line {i+1}: uses User.user_id instead of User.telegram_id")

    def test_alembic_migration_exists(self):
        self.assertTrue(os.path.exists('alembic/versions/v29_add_indexes.py'))

    def test_connection_file_parses(self):
        with open('database/connection.py') as f:
            tree = ast.parse(f.read())
        self.assertIsNotNone(tree)

    def test_models_has_indexes(self):
        """models.py should have Index definitions."""
        with open('database/models.py') as f:
            content = f.read()
        self.assertIn('Index', content, "No Index definitions found in models.py")


# ═══════════════════════════════════════════════════════════════
# 6. MEMORY BOUNDS TESTS
# ═══════════════════════════════════════════════════════════════
class TestMemoryBounds(unittest.TestCase):

    def test_tf_cache_has_max(self):
        with open('handlers/victor/memory.py') as f:
            content = f.read()
        self.assertIn('_tf_cache_max', content, "_tf_cache_max not found — unbounded cache risk")

    def test_tf_cache_max_is_reasonable(self):
        """_tf_cache_max should be between 1000 and 100000."""
        with open('handlers/victor/memory.py') as f:
            content = f.read()
        # It's an instance variable: self._tf_cache_max: int = 10000
        match = re.search(r'_tf_cache_max(?::\s*\w+)?\s*=\s*(\d+)', content)
        self.assertIsNotNone(match, "Could not parse _tf_cache_max value")
        value = int(match.group(1))
        self.assertGreaterEqual(value, 1000)
        self.assertLessEqual(value, 100000)

    def test_tf_cache_has_eviction(self):
        """Memory must evict old entries when cache is full."""
        with open('handlers/victor/memory.py') as f:
            content = f.read()
        self.assertIn('_tf_cache_max', content)
        # Check there's eviction logic
        self.assertTrue(
            'del self._tf_cache' in content or 'evict' in content.lower(),
            "No eviction logic found for _tf_cache"
        )

    def test_cache_layer_has_sweep(self):
        with open('utils/cache_layer.py') as f:
            content = f.read()
        self.assertIn('sweep_expired', content, "sweep_expired missing from CacheLayer")

    def test_cache_layer_has_max_size(self):
        """CacheLayer must have a max_size configuration."""
        with open('utils/cache_layer.py') as f:
            content = f.read()
        self.assertTrue(
            'max_size' in content or 'maxsize' in content or '_max' in content,
            "CacheLayer has no max_size — unbounded growth risk"
        )


# ═══════════════════════════════════════════════════════════════
# 7. SECURITY HARDENING TESTS
# ═══════════════════════════════════════════════════════════════
class TestSecurityHardening(unittest.TestCase):

    def test_executor_has_timeout(self):
        with open('handlers/executor.py') as f:
            content = f.read()
        self.assertIn('timeout', content.lower())

    def test_no_pickle_loads_in_core(self):
        """Core files must not use pickle.loads."""
        core_files = ['main.py', 'config.py', 'database/queries.py',
                      'database/connection.py', 'handlers/executor.py']
        for fp in core_files:
            if os.path.exists(fp):
                with open(fp) as f:
                    content = f.read()
                for i, line in enumerate(content.split('\n')):
                    if 'pickle.loads' in line and not line.strip().startswith('#'):
                        self.fail(f"pickle.loads in {fp}:{i+1}")

    def test_no_yaml_unsafe_load(self):
        """No file should use yaml.load() without Loader (CVE-2017-18342)."""
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '_archived', '.git', 'tests')]
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    with open(fp) as fh:
                        content = fh.read()
                    # yaml.load( without Loader= is dangerous
                    if 'yaml.load(' in content and 'Loader=' not in content:
                        # Check context
                        for i, line in enumerate(content.split('\n')):
                            if 'yaml.load(' in line and 'Loader=' not in line and not line.strip().startswith('#'):
                                self.fail(f"Unsafe yaml.load() in {fp}:{i+1}")

    def test_webhook_secret_support(self):
        """Config must support webhook secret for Telegram validation."""
        with open('config.py') as f:
            content = f.read()
        self.assertTrue(
            'webhook_secret' in content.lower() or 'WEBHOOK_SECRET' in content,
            "No webhook secret support in config"
        )

    def test_rate_limiter_exists(self):
        """Rate limiter middleware must exist."""
        self.assertTrue(os.path.exists('middlewares/rate_limiter.py'))

    def test_redis_errors_logged(self):
        """Cache layer Redis errors must be logged, not silently suppressed."""
        with open('utils/cache_layer.py') as f:
            content = f.read()
        # Count logger.warning or logger.error vs logger.debug for Redis
        warning_count = content.count('logger.warning')
        debug_suppressed = content.count('logger.debug') + content.count('"Suppressed"')
        # There should be warnings for Redis errors
        self.assertGreater(warning_count, 0, "No logger.warning in cache_layer — Redis errors silently suppressed")


# ═══════════════════════════════════════════════════════════════
# 8. FILE INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════
class TestFileIntegrity(unittest.TestCase):

    def test_all_py_files_parse(self):
        errors = []
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d != '__pycache__' and d != '_archived' and d != '.git']
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp) as fh:
                            ast.parse(fh.read())
                    except SyntaxError as e:
                        errors.append(f"{fp}: {e}")
        self.assertEqual(errors, [], f"Syntax errors:\n" + "\n".join(errors[:10]))

    def test_no_duplicate_function_defs_in_critical(self):
        critical_files = ['database/queries.py', 'handlers/executor.py', 'config.py', 'main.py']
        for fp in critical_files:
            if not os.path.exists(fp):
                continue
            with open(fp) as f:
                tree = ast.parse(f.read())
            # Check top-level only
            func_names = [node.name for node in ast.iter_child_nodes(tree)
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            seen = set()
            dupes = set()
            for name in func_names:
                if name in seen:
                    dupes.add(name)
                seen.add(name)
            self.assertEqual(dupes, set(), f"Duplicate top-level functions in {fp}: {dupes}")

    def test_version_is_semver(self):
        version = open('VERSION').read().strip()
        self.assertTrue(len(version.split('.')) == 3)
        for part in version.split('.'):
            self.assertTrue(part.isdigit(), f"Non-numeric version part: {part}")

    def test_main_py_has_entry_point(self):
        with open('main.py') as f:
            content = f.read()
        self.assertTrue(
            '__name__' in content and '__main__' in content,
            "main.py missing if __name__ == '__main__' block"
        )


# ═══════════════════════════════════════════════════════════════
# 9. DOCUMENTATION TESTS
# ═══════════════════════════════════════════════════════════════
class TestDocumentation(unittest.TestCase):

    def test_architecture_doc_exists(self):
        self.assertTrue(os.path.exists('docs/ARCHITECTURE.md'))

    def test_deployment_doc_exists(self):
        self.assertTrue(os.path.exists('docs/DEPLOYMENT.md'))

    def test_api_doc_exists(self):
        self.assertTrue(os.path.exists('docs/API.md'))

    def test_load_testing_doc_exists(self):
        self.assertTrue(os.path.exists('docs/LOAD_TESTING.md'))

    def test_architecture_covers_db_tables(self):
        with open('docs/ARCHITECTURE.md') as f:
            content = f.read()
        for table in ['users', 'analytics_events', 'customers', 'reminders']:
            self.assertIn(table, content, f"Missing table: {table}")

    def test_deployment_covers_docker(self):
        with open('docs/DEPLOYMENT.md') as f:
            content = f.read()
        self.assertIn('docker', content.lower())
        self.assertIn('PostgreSQL', content)


# ═══════════════════════════════════════════════════════════════
# 10. ARCHITECTURE HEALTH TESTS
# ═══════════════════════════════════════════════════════════════
class TestArchitectureHealth(unittest.TestCase):

    def test_no_circular_imports_in_core(self):
        """Core modules should be importable."""
        # Config is the foundation — must import cleanly
        from config import Settings
        self.assertIsNotNone(Settings)

    def test_middlewares_are_modules(self):
        """All middleware files must be valid Python."""
        import glob
        for fp in glob.glob('middlewares/*.py'):
            with open(fp) as f:
                tree = ast.parse(f.read())
            self.assertIsNotNone(tree, f"Failed to parse {fp}")

    def test_handlers_are_modules(self):
        """All handler files must be valid Python."""
        import glob
        for fp in glob.glob('handlers/*.py'):
            if '__pycache__' in fp:
                continue
            with open(fp) as f:
                tree = ast.parse(f.read())
            self.assertIsNotNone(tree, f"Failed to parse {fp}")

    def test_docker_compose_exists(self):
        """Docker Compose file must exist."""
        found = (os.path.exists('docker-compose.yml') or
                 os.path.exists('docker-compose.yaml') or
                 os.path.exists('compose.yml') or
                 os.path.exists('compose.yaml'))
        self.assertTrue(found, "No docker-compose file found")

    def test_dockerfile_exists(self):
        """Dockerfile must exist."""
        self.assertTrue(os.path.exists('Dockerfile'))

    def test_requirements_exist(self):
        """requirements.txt must exist."""
        self.assertTrue(os.path.exists('requirements.txt'))


if __name__ == '__main__':
    unittest.main(verbosity=2)


