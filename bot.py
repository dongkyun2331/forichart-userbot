import argparse
import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from web3 import Web3

APP_DIR = Path(__file__).resolve().parent
ENV_EXAMPLE_PATH = APP_DIR / ".env.example"
ENV_PATH = APP_DIR / ".env"
BSC_DEFAULT_RPC_URL = "https://bsc-dataseed.binance.org"
BSC_DEFAULT_CHAIN_ID = "56"
BSC_DEFAULT_ROUTER_ADDRESS = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
BSC_DEFAULT_V3_ROUTER_ADDRESS = "0x1b81D678ffb9C0263b24A97847620C99d213eB14"
BSC_DEFAULT_V3_QUOTER_ADDRESS = "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997"
BSC_DEFAULT_V3_FEE_TIERS = "500,2500,10000"
NEAR_DEFAULT_API_BASE = "https://cloud-api.near.ai/v1"
NATIVE_BNB_KEY = "native:bnb"
WBNB_ADDRESS = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

ROUTER_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "amountIn", "type": "uint256"}, {"name": "path", "type": "address[]"}],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

V3_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]

V3_QUOTER_ABI = [
    {
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"},
        ],
        "name": "quoteExactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

EXECUTION_GUARD_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "owner", "type": "address"},
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "fromNative", "type": "bool"},
                    {"name": "toNative", "type": "bool"},
                ],
                "name": "intent",
                "type": "tuple",
            },
            {"name": "signature", "type": "bytes"},
        ],
        "name": "executeV3",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]


@dataclass
class Config:
    rpc_url: str
    chain_id: int
    paper_mode: bool
    poll_seconds: int
    signal_url: str
    signal_token: str
    bot_config_url: str
    execution_mode: str
    execution_guard_address: str
    min_confidence: float

    private_key: str
    wallet_address: str

    router_address: str
    v3_router_address: str
    v3_quoter_address: str
    v3_fee_tiers: list[int]
    base_token_address: str
    quote_token_address: str
    base_token_symbol: str
    quote_token_symbol: str
    base_token_decimals: int
    quote_token_decimals: int
    allowed_tokens: set[str]

    buy_amount_base: float
    sell_amount_quote: float

    max_slippage_bps: int
    max_gas_gwei: float
    cooldown_seconds: int
    daily_notional_limit_usd: float

    state_file: str
    trade_log_file: str


def _ensure_env_file() -> None:
    if ENV_PATH.exists():
        return
    if not ENV_EXAMPLE_PATH.exists():
        raise RuntimeError(".env.example 파일이 없어 .env를 생성할 수 없습니다")
    ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print("[setup] .env created automatically (.env.example 기반으로 자동 생성)")


def _upsert_env_value(key: str, value: str) -> None:
    key = key.strip()
    value = value.strip()
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    out: list[str] = []
    replaced = False
    prefix = key + "="
    for line in lines:
        if line.startswith(prefix):
            out.append(prefix + value)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(prefix + value)
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def _ensure_signal_token_interactive() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    token = os.getenv("SIGNAL_TOKEN", "").strip()
    if token:
        return
    if not sys.stdin.isatty():
        raise RuntimeError(
            "SIGNAL_TOKEN이 비어 있습니다. .env의 SIGNAL_TOKEN을 설정하고 다시 실행하세요"
        )
    print("[setup] SIGNAL_TOKEN is missing. 최초 1회 입력이 필요합니다.")
    _set_signal_token_interactive()


def _set_signal_token_interactive(new_token: str | None = None) -> None:
    _ensure_env_file()
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    token = (new_token or "").strip()
    if not token:
        if not sys.stdin.isatty():
            raise RuntimeError("터미널 입력 환경에서만 SIGNAL_TOKEN 변경이 가능합니다")
        token = input("Enter bot token (SIGNAL_TOKEN) / 봇 토큰(SIGNAL_TOKEN)을 입력하세요: ").strip()
    if not token:
        raise RuntimeError("SIGNAL_TOKEN 입력이 비어 있어 실행을 중단합니다")
    _upsert_env_value("SIGNAL_TOKEN", token)
    os.environ["SIGNAL_TOKEN"] = token
    print("[setup] SIGNAL_TOKEN saved to .env / .env에 저장했습니다")


def _mask_secret(value: str, prefix: int = 4, suffix: int = 3) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "(not set)"
    if len(raw) <= (prefix + suffix + 1):
        return "*" * len(raw)
    return f"{raw[:prefix]}...{raw[-suffix:]}"


def _near_api_status_line() -> str:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    base = os.getenv("NEAR_API_BASE", "").strip() or NEAR_DEFAULT_API_BASE
    key = os.getenv("NEAR_API_KEY", "").strip()
    return f"base={base}, key={_mask_secret(key)}"


def _set_near_api_key_interactive(new_key: str | None = None) -> None:
    _ensure_env_file()
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    if not sys.stdin.isatty() and not str(new_key or "").strip():
        raise RuntimeError("터미널 입력 환경에서만 NEAR_API_KEY 변경이 가능합니다")

    current_base = os.getenv("NEAR_API_BASE", "").strip() or NEAR_DEFAULT_API_BASE
    current_key = os.getenv("NEAR_API_KEY", "").strip()

    if sys.stdin.isatty():
        typed_base = input(
            f"NEAR API base (blank=keep) / NEAR API base 입력 (엔터=유지) [{current_base}]: "
        ).strip()
        near_api_base = typed_base or current_base
    else:
        near_api_base = current_base
    _upsert_env_value("NEAR_API_BASE", near_api_base)
    os.environ["NEAR_API_BASE"] = near_api_base

    key = (new_key or "").strip()
    if not key:
        prompt = (
            "Enter NEAR_API_KEY (blank=keep current) / "
            "NEAR_API_KEY 입력 (엔터=유지): "
        )
        key = input(prompt).strip() if sys.stdin.isatty() else ""
    if not key:
        key = current_key
    if not key:
        raise RuntimeError("NEAR_API_KEY가 비어 있습니다")

    _upsert_env_value("NEAR_API_KEY", key)
    os.environ["NEAR_API_KEY"] = key
    print("[setup] NEAR_API_KEY saved to .env / .env에 저장했습니다")
    print(f"[setup] NEAR API status / 상태: {_near_api_status_line()}")


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _current_mode_name() -> str:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    return "paper" if _is_truthy(os.getenv("PAPER_MODE", "1")) else "live"


def _set_mode(mode: str) -> None:
    mode_norm = str(mode or "").strip().lower()
    if mode_norm not in {"paper", "live"}:
        raise RuntimeError("mode must be paper or live")
    value = "1" if mode_norm == "paper" else "0"
    _upsert_env_value("PAPER_MODE", value)
    os.environ["PAPER_MODE"] = value
    print(f"[setup] mode changed to {mode_norm} / 모드 변경됨: {mode_norm}")


def _ensure_bsc_defaults() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    defaults = {
        "RPC_URL": BSC_DEFAULT_RPC_URL,
        "CHAIN_ID": BSC_DEFAULT_CHAIN_ID,
        "ROUTER_ADDRESS": BSC_DEFAULT_ROUTER_ADDRESS,
        "V3_ROUTER_ADDRESS": BSC_DEFAULT_V3_ROUTER_ADDRESS,
        "V3_QUOTER_ADDRESS": BSC_DEFAULT_V3_QUOTER_ADDRESS,
        "V3_FEE_TIERS": BSC_DEFAULT_V3_FEE_TIERS,
    }
    for key, fallback in defaults.items():
        current = os.getenv(key, "").strip()
        if current:
            continue
        _upsert_env_value(key, fallback)
        os.environ[key] = fallback
        print(f"[setup] {key} BSC default applied / 기본값 적용: {fallback}")


def _ensure_live_wallet_interactive() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    paper_mode = _is_truthy(os.getenv("PAPER_MODE", "1"))
    if paper_mode:
        return
    if not sys.stdin.isatty():
        raise RuntimeError(
            "PAPER_MODE=0인데 PRIVATE_KEY/WALLET_ADDRESS가 비어 있습니다. .env를 먼저 설정하세요"
        )

    private_key = os.getenv("PRIVATE_KEY", "").strip()
    if not private_key:
        typed = input("Enter PRIVATE_KEY for live mode / 실거래 모드 PRIVATE_KEY를 입력하세요: ").strip()
        if not typed:
            raise RuntimeError("PRIVATE_KEY 입력이 비어 있어 실행을 중단합니다")
        private_key = typed
        _upsert_env_value("PRIVATE_KEY", private_key)
        os.environ["PRIVATE_KEY"] = private_key
        print("[setup] PRIVATE_KEY saved to .env / .env에 저장했습니다")

    wallet_address = os.getenv("WALLET_ADDRESS", "").strip()
    if wallet_address:
        return

    derived = ""
    try:
        derived = str(Web3().eth.account.from_key(private_key).address or "").strip()
    except Exception:
        derived = ""

    prompt = "Enter WALLET_ADDRESS for live mode / 실거래 모드 WALLET_ADDRESS를 입력하세요"
    if derived:
        prompt += f" (엔터 시 {derived})"
    prompt += ": "
    typed_wallet = input(prompt).strip()
    if not typed_wallet:
        typed_wallet = derived
    if not typed_wallet:
        raise RuntimeError("WALLET_ADDRESS 입력이 비어 있어 실행을 중단합니다")

    _upsert_env_value("WALLET_ADDRESS", typed_wallet)
    os.environ["WALLET_ADDRESS"] = typed_wallet
    print("[setup] WALLET_ADDRESS saved to .env / .env에 저장했습니다")


def _set_wallet_credentials_interactive() -> None:
    _ensure_env_file()
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    if not sys.stdin.isatty():
        raise RuntimeError("터미널 입력 환경에서만 지갑 키 설정이 가능합니다")

    current_pk = os.getenv("PRIVATE_KEY", "").strip()
    current_wallet = os.getenv("WALLET_ADDRESS", "").strip()

    typed_pk = input("Enter PRIVATE_KEY (blank=keep current) / PRIVATE_KEY 입력 (엔터=유지): ").strip()
    private_key = typed_pk or current_pk
    if not private_key:
        raise RuntimeError("PRIVATE_KEY가 비어 있습니다")
    if typed_pk:
        _upsert_env_value("PRIVATE_KEY", private_key)
        os.environ["PRIVATE_KEY"] = private_key
        print("[setup] PRIVATE_KEY saved to .env / .env에 저장했습니다")

    derived = ""
    try:
        derived = str(Web3().eth.account.from_key(private_key).address or "").strip()
    except Exception:
        derived = ""

    default_wallet = current_wallet or derived
    wallet_prompt = "Enter WALLET_ADDRESS (blank=keep/default) / WALLET_ADDRESS 입력 (엔터=유지)"
    if default_wallet:
        wallet_prompt += f" [{default_wallet}]"
    wallet_prompt += ": "
    typed_wallet = input(wallet_prompt).strip()
    wallet_address = typed_wallet or default_wallet
    if not wallet_address:
        raise RuntimeError("WALLET_ADDRESS가 비어 있습니다")
    _upsert_env_value("WALLET_ADDRESS", wallet_address)
    os.environ["WALLET_ADDRESS"] = wallet_address
    print("[setup] WALLET_ADDRESS saved to .env / .env에 저장했습니다")


def _load_remote_bot_config(config_url: str, bot_token: str) -> Dict[str, Any]:
    if not config_url or not bot_token:
        return {}
    try:
        res = requests.get(
            config_url,
            headers={"Authorization": f"Bearer {bot_token}"},
            timeout=10,
        )
        if res.status_code == 404:
            print("[config] remote config not found, fallback to .env")
            return {}
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, dict):
            print("[config] invalid remote payload, fallback to .env")
            return {}
        print("[config] loaded from backend")
        return data
    except Exception as e:
        print(f"[config] remote fetch failed: {e}, fallback to .env")
        return {}


def _parse_fee_tiers(raw: str) -> list[int]:
    out: list[int] = []
    for part in str(raw or "").split(","):
        value = part.strip()
        if not value:
            continue
        try:
            fee = int(value)
        except Exception:
            continue
        if fee <= 0 or fee > 1_000_000:
            continue
        if fee not in out:
            out.append(fee)
    if not out:
        out = [500, 2500, 10000]
    return out


class SwapBot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.w3 = Web3(Web3.HTTPProvider(cfg.rpc_url, request_kwargs={"timeout": 20}))
        if not self.w3.is_connected():
            raise RuntimeError("RPC 연결 실패")

        self.v2_router = None
        if cfg.router_address:
            self.v2_router = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.router_address), abi=ROUTER_ABI
            )
        self.v3_router = None
        self.v3_quoter = None
        if cfg.v3_router_address and cfg.v3_quoter_address:
            self.v3_router = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.v3_router_address),
                abi=V3_ROUTER_ABI,
            )
            self.v3_quoter = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.v3_quoter_address),
                abi=V3_QUOTER_ABI,
            )
        self.execution_guard = None
        if cfg.execution_guard_address:
            self.execution_guard = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.execution_guard_address),
                abi=EXECUTION_GUARD_ABI,
            )
        self.base_token = None
        if not self._is_native_token(cfg.base_token_address):
            self.base_token = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.base_token_address), abi=ERC20_ABI
            )
        self.quote_token = None
        if not self._is_native_token(cfg.quote_token_address):
            self.quote_token = self.w3.eth.contract(
                address=Web3.to_checksum_address(cfg.quote_token_address), abi=ERC20_ABI
            )

        self.state_path = Path(cfg.state_file)
        self.log_path = Path(cfg.trade_log_file)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

        self._validate_config()

    def _validate_config(self) -> None:
        mode = str(self.cfg.execution_mode or "direct").strip().lower()
        if mode not in {"direct", "guard", "auto"}:
            raise RuntimeError("EXECUTION_MODE must be direct, guard, or auto")
        required = {
            self.cfg.base_token_address.lower(),
            self.cfg.quote_token_address.lower(),
        }
        if not required.issubset(self.cfg.allowed_tokens):
            raise RuntimeError("BASE/QUOTE 토큰이 ALLOWED_TOKENS에 포함되어야 합니다")
        if self.cfg.max_slippage_bps <= 0 or self.cfg.max_slippage_bps > 2000:
            raise RuntimeError("MAX_SLIPPAGE_BPS 범위가 잘못되었습니다 (1~2000)")
        if not self.cfg.router_address and not self.cfg.v3_router_address:
            raise RuntimeError("ROUTER_ADDRESS 또는 V3_ROUTER_ADDRESS 중 하나는 필요합니다")
        if not self.cfg.paper_mode:
            if not self.cfg.private_key or not self.cfg.wallet_address:
                raise RuntimeError("LIVE 모드는 PRIVATE_KEY/WALLET_ADDRESS가 필요합니다")
            if mode == "guard" and not self.cfg.execution_guard_address:
                raise RuntimeError("guard 모드는 EXECUTION_GUARD_ADDRESS가 필요합니다")

    @staticmethod
    def _is_native_token(token: str) -> bool:
        return str(token or "").strip().lower() in {NATIVE_BNB_KEY, "native_bnb", "bnb"}

    def _token_for_router(self, token: str) -> str:
        if self._is_native_token(token):
            return WBNB_ADDRESS
        return token

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {
                "last_trade_ts": 0,
                "day": self._day_key(),
                "daily_notional_usd": 0.0,
                "open_position": None,
            }
        try:
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                loaded = {}
            loaded.setdefault("last_trade_ts", 0)
            loaded.setdefault("day", self._day_key())
            loaded.setdefault("daily_notional_usd", 0.0)
            loaded.setdefault("open_position", None)
            return loaded
        except Exception:
            return {
                "last_trade_ts": 0,
                "day": self._day_key(),
                "daily_notional_usd": 0.0,
                "open_position": None,
            }

    def _save_state(self) -> None:
        self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _day_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _roll_day_if_needed(self) -> None:
        now_day = self._day_key()
        if self.state.get("day") != now_day:
            self.state["day"] = now_day
            self.state["daily_notional_usd"] = 0.0
            self._save_state()

    def _append_log(self, payload: Dict[str, Any]) -> None:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _normalize_signal_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        action = str(data.get("action", "HOLD")).upper()
        confidence = float(data.get("confidence", 0.0))
        reason = str(data.get("reason", ""))[:240]
        amount_usd = data.get("amount_usd")
        trigger_price = data.get("trigger_price")
        trigger_condition = str(data.get("trigger_condition", "")).upper().strip()
        take_profit_price = data.get("take_profit_price")
        stop_price = data.get("stop_price")
        if trigger_condition not in {"GTE", "LTE"}:
            trigger_condition = ""
        try:
            trigger_price = float(trigger_price) if trigger_price is not None else None
        except Exception:
            trigger_price = None
        try:
            take_profit_price = float(take_profit_price) if take_profit_price is not None else None
        except Exception:
            take_profit_price = None
        try:
            stop_price = float(stop_price) if stop_price is not None else None
        except Exception:
            stop_price = None
        try:
            amount_usd = float(amount_usd) if amount_usd is not None else None
        except Exception:
            amount_usd = None
        if trigger_price is not None and (not trigger_price > 0):
            trigger_price = None
        if take_profit_price is not None and (not take_profit_price > 0):
            take_profit_price = None
        if stop_price is not None and (not stop_price > 0):
            stop_price = None
        if amount_usd is not None and (not amount_usd > 0):
            amount_usd = None
        if action not in {"BUY", "SELL", "HOLD"}:
            action = "HOLD"
        return {
            "signal_id": str(data.get("signal_id", "")).strip(),
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "amount_usd": amount_usd,
            "trigger_price": trigger_price,
            "trigger_condition": trigger_condition,
            "take_profit_price": take_profit_price,
            "stop_price": stop_price,
            "intent": data.get("intent") if isinstance(data.get("intent"), dict) else None,
            "signature": str(data.get("signature", "")).strip() or None,
        }

    @staticmethod
    def _as_pos_float(value: Any) -> float | None:
        try:
            v = float(value)
            if v > 0:
                return v
            return None
        except Exception:
            return None

    def _active_position(self) -> Dict[str, Any] | None:
        p = self.state.get("open_position")
        return p if isinstance(p, dict) else None

    def _clear_position(self) -> None:
        if self.state.get("open_position") is None:
            return
        self.state["open_position"] = None
        self._save_state()

    def _set_position_after_buy(self, signal: Dict[str, Any], result: Dict[str, Any]) -> None:
        tp = self._as_pos_float(signal.get("take_profit_price"))
        sp = self._as_pos_float(signal.get("stop_price"))
        if tp is None and sp is None:
            return
        amount_out_est = 0
        try:
            amount_out_est = int(result.get("amount_out_est") or 0)
        except Exception:
            amount_out_est = 0
        if amount_out_est <= 0:
            try:
                amount_out_est = int((result.get("route") or {}).get("amount_out") or 0)
            except Exception:
                amount_out_est = 0
        if amount_out_est <= 0:
            try:
                amount_out_est = int(result.get("amount_out_min") or 0)
            except Exception:
                amount_out_est = 0
        exit_amount_quote = (
            float(amount_out_est) / float(10 ** int(self.cfg.quote_token_decimals))
            if amount_out_est > 0
            else self._as_pos_float(signal.get("amount_usd"))
        )
        if exit_amount_quote is None or exit_amount_quote <= 0:
            return
        self.state["open_position"] = {
            "entry_signal_id": str(signal.get("signal_id", "")).strip(),
            "entry_action": "BUY",
            "take_profit_price": tp,
            "stop_price": sp,
            "exit_amount_quote": float(exit_amount_quote),
            "opened_at": int(time.time()),
            "last_price": None,
        }
        self._save_state()
        print(
            f"[position] armed tp/sp tp={tp if tp is not None else '-'} "
            f"sp={sp if sp is not None else '-'} exit_quote={exit_amount_quote:.8f}"
        )

    def _sync_position_after_trade(self, signal: Dict[str, Any], result: Dict[str, Any]) -> None:
        action = str(signal.get("action", "")).upper().strip()
        if action == "BUY":
            self._set_position_after_buy(signal, result)
            return
        if action == "SELL":
            self._clear_position()

    def _evaluate_position_exit(self) -> tuple[bool, str, Dict[str, Any] | None]:
        pos = self._active_position()
        if not pos:
            return False, "no_position", None
        if str(pos.get("entry_action", "")).upper() != "BUY":
            self._clear_position()
            return False, "invalid_position", None

        tp = self._as_pos_float(pos.get("take_profit_price"))
        sp = self._as_pos_float(pos.get("stop_price"))
        if tp is None and sp is None:
            self._clear_position()
            return False, "empty_tp_sp", None

        current_price = self._get_pair_price_quote_per_base()
        if not current_price > 0:
            return False, "price_unavailable", None
        pos["last_price"] = current_price
        self.state["open_position"] = pos
        self._save_state()

        if tp is not None and current_price >= tp:
            return True, f"TP hit {current_price:.8f} >= {tp:.8f}", pos
        if sp is not None and current_price <= sp:
            return True, f"SP hit {current_price:.8f} <= {sp:.8f}", pos
        return False, f"대기: price={current_price:.8f} tp={tp} sp={sp}", pos

    def _execute_position_exit_if_needed(self) -> bool:
        should_exit, reason, pos = self._evaluate_position_exit()
        if not should_exit:
            if pos and not reason.startswith("대기:"):
                print(f"[position] {reason}")
            return False
        if not pos:
            return False

        exit_amount_quote = self._as_pos_float(pos.get("exit_amount_quote"))
        if exit_amount_quote is None:
            self._clear_position()
            raise RuntimeError("open_position exit amount 값이 올바르지 않습니다")

        synthetic_signal: Dict[str, Any] = {
            "signal_id": f"local_exit_{int(time.time())}",
            "action": "SELL",
            "confidence": 1.0,
            "reason": f"AUTO_EXIT {reason}",
            "amount_usd": float(exit_amount_quote),
            "trigger_price": None,
            "trigger_condition": "",
            "take_profit_price": None,
            "stop_price": None,
            "intent": None,
            "signature": None,
        }
        print(f"[position] auto-exit start: {reason} amount_quote={exit_amount_quote:.8f}")
        if self.cfg.paper_mode:
            result = self._paper_swap(synthetic_signal)
        else:
            # auto exit is local risk management path, so it is executed directly.
            result = self._live_swap(synthetic_signal)
        self._increase_notional(float(result.get("amount_used") or 0.0))
        self._append_log({"status": "executed", "signal": synthetic_signal, "result": result})
        print(f"[executed] {result}")
        self._clear_position()
        return True

    def _pending_signal_url(self) -> str:
        url = str(self.cfg.signal_url or "").strip()
        if url.endswith("/bot/signal"):
            return url + "/pending"
        if url.endswith("/bot/signal/"):
            return url + "pending"
        return url

    def _consume_signal_url(self, signal_id: str) -> str:
        base = str(self.cfg.signal_url or "").strip().rstrip("/")
        return f"{base}/{signal_id}/consume"

    def _auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.cfg.signal_token:
            headers["Authorization"] = f"Bearer {self.cfg.signal_token}"
        return headers

    def _fetch_signals(self) -> list[Dict[str, Any]]:
        headers = self._auth_headers()
        pending_url = self._pending_signal_url()
        try:
            res = requests.get(pending_url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                return []
            out: list[Dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                out.append(self._normalize_signal_payload(item))
            return out
        except Exception:
            # fallback: single-signal API compatibility
            res = requests.get(self.cfg.signal_url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if not isinstance(data, dict):
                return []
            return [self._normalize_signal_payload(data)]

    def _consume_signal(self, signal_id: str, tx_hash: str | None = None, note: str | None = None) -> None:
        sid = str(signal_id or "").strip()
        if not sid:
            return
        payload: Dict[str, Any] = {}
        if tx_hash:
            payload["tx_hash"] = str(tx_hash).strip()
        if note:
            payload["note"] = str(note).strip()[:500]
        try:
            requests.post(
                self._consume_signal_url(sid),
                headers=self._auth_headers(),
                json=payload if payload else {},
                timeout=10,
            ).raise_for_status()
        except Exception as e:
            print(f"[warn] consume failed sid={sid}: {e}")

    def _get_pair_price_quote_per_base(self) -> float:
        amount_in = 10 ** int(self.cfg.base_token_decimals)
        best = self._select_best_route(
            amount_in=amount_in,
            token_in=self.cfg.base_token_address,
            token_out=self.cfg.quote_token_address,
        )
        out_raw = int(best["amount_out"])
        return float(out_raw) / float(10 ** int(self.cfg.quote_token_decimals))

    def _is_trigger_price_matched(self, signal: Dict[str, Any]) -> tuple[bool, str]:
        trigger_price = signal.get("trigger_price")
        trigger_condition = str(signal.get("trigger_condition", "")).upper().strip()
        if trigger_price is None or trigger_condition not in {"GTE", "LTE"}:
            return True, "ok"
        current_price = self._get_pair_price_quote_per_base()
        if not current_price > 0:
            return False, "트리거 현재가 조회 실패"
        if trigger_condition == "GTE":
            if current_price >= float(trigger_price):
                return True, "ok"
            return False, f"트리거 대기: {current_price:.8f} < {float(trigger_price):.8f}"
        if current_price <= float(trigger_price):
            return True, "ok"
        return False, f"트리거 대기: {current_price:.8f} > {float(trigger_price):.8f}"

    def _guard_ok(self, signal: Dict[str, Any], skip_cooldown: bool = False) -> tuple[bool, str]:
        self._roll_day_if_needed()
        now_ts = int(time.time())

        if signal["action"] == "HOLD":
            return False, "신호 HOLD"

        trigger_ok, trigger_reason = self._is_trigger_price_matched(signal)
        if not trigger_ok:
            return False, trigger_reason

        if (not skip_cooldown) and now_ts - int(self.state.get("last_trade_ts", 0)) < self.cfg.cooldown_seconds:
            return False, "쿨다운 중"

        if float(self.state.get("daily_notional_usd", 0.0)) >= self.cfg.daily_notional_limit_usd:
            return False, "일일 한도 초과"

        gas_gwei = self.w3.from_wei(self.w3.eth.gas_price, "gwei")
        if float(gas_gwei) > self.cfg.max_gas_gwei:
            return False, f"가스 과다 {gas_gwei:.2f} gwei"

        return True, "ok"

    def _amount_in(self, action: str, signal_amount: float | None = None) -> tuple[int, str, str, int, float]:
        if action == "BUY":
            amount = float(signal_amount) if signal_amount and signal_amount > 0 else self.cfg.buy_amount_base
            decimals = self.cfg.base_token_decimals
            token_in = self.cfg.base_token_address
            token_out = self.cfg.quote_token_address
        else:
            amount = float(signal_amount) if signal_amount and signal_amount > 0 else self.cfg.sell_amount_quote
            decimals = self.cfg.quote_token_decimals
            token_in = self.cfg.quote_token_address
            token_out = self.cfg.base_token_address

        amount_wei = int(amount * (10 ** decimals))
        if amount_wei <= 0:
            raise RuntimeError("주문 수량이 0 이하")
        return amount_wei, token_in, token_out, decimals, float(amount)

    def _quote_v2(self, amount_in: int, token_in: str, token_out: str) -> int | None:
        if not self.v2_router or not self.cfg.router_address:
            return None
        try:
            token_in_router = self._token_for_router(token_in)
            token_out_router = self._token_for_router(token_out)
            path = [Web3.to_checksum_address(token_in_router), Web3.to_checksum_address(token_out_router)]
            amounts = self.v2_router.functions.getAmountsOut(amount_in, path).call()
            if not amounts or int(amounts[-1]) <= 0:
                return None
            return int(amounts[-1])
        except Exception:
            return None

    def _quote_v3_one(self, amount_in: int, token_in: str, token_out: str, fee: int) -> int | None:
        if not self.v3_quoter:
            return None
        token_in_cs = Web3.to_checksum_address(self._token_for_router(token_in))
        token_out_cs = Web3.to_checksum_address(self._token_for_router(token_out))
        try:
            out = self.v3_quoter.functions.quoteExactInputSingle(
                token_in_cs,
                token_out_cs,
                int(fee),
                int(amount_in),
                0,
            ).call()
            if isinstance(out, (list, tuple)):
                out = out[0]
            out_int = int(out)
            return out_int if out_int > 0 else None
        except Exception:
            pass
        try:
            out = self.v3_quoter.functions.quoteExactInputSingle(
                (token_in_cs, token_out_cs, int(amount_in), int(fee), 0)
            ).call()
            if isinstance(out, (list, tuple)):
                out = out[0]
            out_int = int(out)
            return out_int if out_int > 0 else None
        except Exception:
            return None

    def _select_best_route(self, amount_in: int, token_in: str, token_out: str) -> Dict[str, Any]:
        candidates: list[Dict[str, Any]] = []
        v2_out = self._quote_v2(amount_in, token_in, token_out)
        if v2_out and v2_out > 0:
            candidates.append({"venue": "v2", "amount_out": int(v2_out)})

        token_in_native = self._is_native_token(token_in)
        token_out_native = self._is_native_token(token_out)
        if not token_in_native and not token_out_native:
            for fee in self.cfg.v3_fee_tiers:
                out = self._quote_v3_one(amount_in, token_in, token_out, fee)
                if out and out > 0:
                    candidates.append({"venue": "v3", "fee": int(fee), "amount_out": int(out)})

        if not candidates:
            raise RuntimeError("견적 실패(v2/v3)")
        candidates.sort(key=lambda item: int(item.get("amount_out", 0)), reverse=True)
        return candidates[0]

    def _ensure_allowance(self, token_contract, amount_in: int, spender_address: str) -> str | None:
        if token_contract is None:
            return None
        wallet = Web3.to_checksum_address(self.cfg.wallet_address)
        spender = Web3.to_checksum_address(spender_address)
        allowance = token_contract.functions.allowance(wallet, spender).call()
        if int(allowance) >= int(amount_in):
            return None

        nonce = self.w3.eth.get_transaction_count(wallet)
        tx = token_contract.functions.approve(spender, 2**256 - 1).build_transaction(
            {
                "from": wallet,
                "nonce": nonce,
                "chainId": self.cfg.chain_id,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)
        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.cfg.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if receipt.status != 1:
            raise RuntimeError("approve 실패")
        return tx_hash.hex()

    def _live_swap(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        action = signal["action"]
        amount_in, token_in, token_out, _, amount_used = self._amount_in(
            action,
            signal.get("amount_usd"),
        )
        token_in_native = self._is_native_token(token_in)
        token_out_native = self._is_native_token(token_out)
        token_in_router = self._token_for_router(token_in)
        token_out_router = self._token_for_router(token_out)
        token_in_cs = Web3.to_checksum_address(token_in_router)
        token_out_cs = Web3.to_checksum_address(token_out_router)
        route = self._select_best_route(amount_in, token_in, token_out)
        out_expected = int(route["amount_out"])
        amount_out_min = int(out_expected * (10000 - self.cfg.max_slippage_bps) / 10000)
        if amount_out_min <= 0:
            raise RuntimeError("amountOutMin 계산 실패")
        if route.get("venue") == "v3" and (token_in_native or token_out_native):
            raise RuntimeError("BNB 네이티브 스왑은 v2 라우터에서만 지원합니다")

        token_contract = self.base_token if action == "BUY" else self.quote_token
        spender = (
            self.cfg.router_address
            if route.get("venue") == "v2"
            else self.cfg.v3_router_address
        )
        if not spender:
            raise RuntimeError("라우터 주소가 비어 있습니다")
        approve_hash = self._ensure_allowance(token_contract, amount_in, spender)

        wallet = Web3.to_checksum_address(self.cfg.wallet_address)
        nonce = self.w3.eth.get_transaction_count(wallet)
        deadline = int(time.time()) + 600
        if route.get("venue") == "v2":
            path = [token_in_cs, token_out_cs]
            if token_in_native:
                tx = self.v2_router.functions.swapExactETHForTokens(
                    amount_out_min,
                    path,
                    wallet,
                    deadline,
                ).build_transaction(
                    {
                        "from": wallet,
                        "nonce": nonce,
                        "chainId": self.cfg.chain_id,
                        "gasPrice": self.w3.eth.gas_price,
                        "value": amount_in,
                    }
                )
            elif token_out_native:
                tx = self.v2_router.functions.swapExactTokensForETH(
                    amount_in,
                    amount_out_min,
                    path,
                    wallet,
                    deadline,
                ).build_transaction(
                    {
                        "from": wallet,
                        "nonce": nonce,
                        "chainId": self.cfg.chain_id,
                        "gasPrice": self.w3.eth.gas_price,
                    }
                )
            else:
                tx = self.v2_router.functions.swapExactTokensForTokens(
                    amount_in,
                    amount_out_min,
                    path,
                    wallet,
                    deadline,
                ).build_transaction(
                    {
                        "from": wallet,
                        "nonce": nonce,
                        "chainId": self.cfg.chain_id,
                        "gasPrice": self.w3.eth.gas_price,
                    }
                )
        else:
            if not self.v3_router:
                raise RuntimeError("V3 router가 설정되지 않았습니다")
            fee = int(route.get("fee", 0))
            if fee <= 0:
                raise RuntimeError("V3 fee tier가 올바르지 않습니다")
            tx = self.v3_router.functions.exactInputSingle(
                (
                    token_in_cs,
                    token_out_cs,
                    fee,
                    wallet,
                    amount_in,
                    amount_out_min,
                    0,
                )
            ).build_transaction(
                {
                    "from": wallet,
                    "nonce": nonce,
                    "chainId": self.cfg.chain_id,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
        tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)

        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.cfg.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if receipt.status != 1:
            raise RuntimeError("swap 실패")

        return {
            "mode": "live",
            "action": action,
            "route": route,
            "amount_used": amount_used,
            "amount_in": amount_in,
            "amount_out_min": amount_out_min,
            "amount_out_est": out_expected,
            "tx_hash": tx_hash.hex(),
            "approve_hash": approve_hash,
        }

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            if isinstance(value, str):
                v = value.strip()
                if v.startswith(("0x", "0X")):
                    return int(v, 16)
                return int(v)
            return int(value)
        except Exception:
            return int(default)

    def _live_swap_guard(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not self.execution_guard or not self.cfg.execution_guard_address:
            raise RuntimeError("ExecutionGuard 컨트랙트가 설정되지 않았습니다")
        intent = signal.get("intent")
        if not isinstance(intent, dict):
            raise RuntimeError("guard 실행에 필요한 intent가 없습니다")
        signature = str(signal.get("signature") or "").strip()
        if not signature:
            raise RuntimeError("guard 실행에 필요한 signature가 없습니다")

        owner = Web3.to_checksum_address(str(intent.get("owner") or self.cfg.wallet_address))
        token_in = Web3.to_checksum_address(str(intent.get("tokenIn") or intent.get("token_in") or ""))
        token_out = Web3.to_checksum_address(str(intent.get("tokenOut") or intent.get("token_out") or ""))
        fee = self._to_int(intent.get("fee"), 2500)
        recipient = Web3.to_checksum_address(
            str(intent.get("recipient") or self.cfg.wallet_address)
        )
        amount_in = self._to_int(intent.get("amountIn") or intent.get("amount_in"), 0)
        amount_out_min = self._to_int(intent.get("amountOutMin") or intent.get("amount_out_min"), 0)
        deadline = self._to_int(intent.get("deadline"), 0)
        nonce_intent = self._to_int(intent.get("nonce"), 0)
        from_native = bool(intent.get("fromNative") if "fromNative" in intent else intent.get("from_native"))
        to_native = bool(intent.get("toNative") if "toNative" in intent else intent.get("to_native"))

        if amount_in <= 0 or amount_out_min <= 0:
            raise RuntimeError("guard intent amount 값이 올바르지 않습니다")
        if deadline <= 0:
            raise RuntimeError("guard intent deadline 값이 올바르지 않습니다")

        intent_tuple = (
            owner,
            token_in,
            token_out,
            int(fee),
            recipient,
            int(amount_in),
            int(amount_out_min),
            int(deadline),
            int(nonce_intent),
            bool(from_native),
            bool(to_native),
        )

        wallet = Web3.to_checksum_address(self.cfg.wallet_address)
        nonce = self.w3.eth.get_transaction_count(wallet)
        tx_params: Dict[str, Any] = {
            "from": wallet,
            "nonce": nonce,
            "chainId": self.cfg.chain_id,
            "gasPrice": self.w3.eth.gas_price,
        }
        if from_native:
            tx_params["value"] = int(amount_in)

        tx = self.execution_guard.functions.executeV3(intent_tuple, signature).build_transaction(
            tx_params
        )
        tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)

        signed = self.w3.eth.account.sign_transaction(tx, private_key=self.cfg.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if receipt.status != 1:
            raise RuntimeError("guard execute 실패")

        amount_used = (
            float(signal.get("amount_usd"))
            if signal.get("amount_usd") and float(signal.get("amount_usd")) > 0
            else (self.cfg.buy_amount_base if signal.get("action") == "BUY" else self.cfg.sell_amount_quote)
        )
        return {
            "mode": "live",
            "path": "guard",
            "action": signal.get("action"),
            "amount_used": float(amount_used),
            "amount_in": int(amount_in),
            "amount_out_min": int(amount_out_min),
            "amount_out_est": int(amount_out_min),
            "tx_hash": tx_hash.hex(),
            "guard_address": self.cfg.execution_guard_address,
        }

    def _paper_swap(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        action = signal["action"]
        amount_in, token_in, token_out, _, amount_used = self._amount_in(
            action,
            signal.get("amount_usd"),
        )
        route = self._select_best_route(amount_in, token_in, token_out)
        out_expected = int(route["amount_out"])
        amount_out_min = int(out_expected * (10000 - self.cfg.max_slippage_bps) / 10000)
        return {
            "mode": "paper",
            "action": action,
            "route": route,
            "amount_used": amount_used,
            "amount_in": amount_in,
            "amount_out_min": amount_out_min,
            "amount_out_est": out_expected,
            "tx_hash": "paper-simulated",
        }

    def _increase_notional(self, amount_used: float) -> None:
        add = float(amount_used) if amount_used and amount_used > 0 else 0.0
        self.state["daily_notional_usd"] = float(self.state.get("daily_notional_usd", 0.0)) + add
        self.state["last_trade_ts"] = int(time.time())
        self._save_state()

    def run_once(self) -> None:
        try:
            self._execute_position_exit_if_needed()
        except Exception as e:
            self._append_log({"status": "error", "error": str(e), "signal": {"action": "SELL", "reason": "AUTO_EXIT"}})
            print(f"[error] auto-exit failed: {e}")

        signals = self._fetch_signals()
        if not signals:
            self._append_log({"status": "skip", "reason": "대기 신호 없음", "signal": {"action": "HOLD"}})
            print("[skip] 대기 신호 없음")
            return

        executed_count = 0
        for signal in signals:
            ok, reason = self._guard_ok(signal, skip_cooldown=(executed_count > 0))
            if not ok:
                self._append_log({"status": "skip", "reason": reason, "signal": signal})
                print(f"[skip] {reason} signal={signal}")
                continue
            try:
                if self.cfg.paper_mode:
                    result = self._paper_swap(signal)
                else:
                    mode = str(self.cfg.execution_mode or "direct").strip().lower()
                    has_guard_payload = bool(
                        self.execution_guard
                        and isinstance(signal.get("intent"), dict)
                        and str(signal.get("signature") or "").strip()
                    )
                    if mode == "guard":
                        result = self._live_swap_guard(signal)
                    elif mode == "auto" and has_guard_payload:
                        result = self._live_swap_guard(signal)
                    else:
                        result = self._live_swap(signal)
                self._increase_notional(float(result.get("amount_used") or 0.0))
                self._sync_position_after_trade(signal, result)
                self._append_log({"status": "executed", "signal": signal, "result": result})
                print(f"[executed] {result}")
                self._consume_signal(
                    signal.get("signal_id", ""),
                    tx_hash=str(result.get("tx_hash") or ""),
                    note="executed",
                )
                executed_count += 1
            except Exception as e:
                self._append_log({"status": "error", "error": str(e), "signal": signal})
                print(f"[error] {e} signal={signal}")



def build_config() -> Config:
    _ensure_env_file()
    _ensure_signal_token_interactive()
    _ensure_bsc_defaults()
    _ensure_live_wallet_interactive()
    load_dotenv(dotenv_path=ENV_PATH, override=False)

    def env(name: str, default: str = "") -> str:
        return os.getenv(name, default).strip()

    allowed_tokens = {
        x.strip().lower()
        for x in env("ALLOWED_TOKENS", "").split(",")
        if x.strip()
    }
    signal_token = env("SIGNAL_TOKEN")
    bot_config_url = env("BOT_CONFIG_URL", "https://api.fori.kr/api/bot/config")
    remote = _load_remote_bot_config(bot_config_url, signal_token)

    def pick_str(name: str, fallback: str) -> str:
        value = remote.get(name)
        if value is None:
            return fallback
        return str(value).strip()

    def pick_int(name: str, fallback: int) -> int:
        value = remote.get(name)
        if value is None:
            return fallback
        try:
            return int(value)
        except Exception:
            return fallback

    def pick_float(name: str, fallback: float) -> float:
        value = remote.get(name)
        if value is None:
            return fallback
        try:
            return float(value)
        except Exception:
            return fallback

    def normalize_pair_token(value: str) -> str:
        v = str(value or "").strip().lower()
        if v in {"bnb", "native:bnb", "native_bnb"}:
            return NATIVE_BNB_KEY
        return v

    base_token_address = normalize_pair_token(
        pick_str("base_token_address", env("BASE_TOKEN_ADDRESS"))
    )
    quote_token_address = normalize_pair_token(
        pick_str("quote_token_address", env("QUOTE_TOKEN_ADDRESS"))
    )
    if base_token_address:
        allowed_tokens.add(base_token_address)
    if quote_token_address:
        allowed_tokens.add(quote_token_address)

    return Config(
        rpc_url=env("RPC_URL"),
        chain_id=int(env("CHAIN_ID", "56")),
        paper_mode=env("PAPER_MODE", "1") in {"1", "true", "TRUE", "yes", "YES"},
        poll_seconds=int(env("POLL_SECONDS", "1")),
        signal_url=env("SIGNAL_URL"),
        signal_token=signal_token,
        bot_config_url=bot_config_url,
        execution_mode=env("EXECUTION_MODE", "direct").lower(),
        execution_guard_address=env("EXECUTION_GUARD_ADDRESS"),
        min_confidence=pick_float("min_confidence", float(env("MIN_CONFIDENCE", "0.65"))),
        private_key=env("PRIVATE_KEY"),
        wallet_address=env("WALLET_ADDRESS"),
        router_address=env("ROUTER_ADDRESS"),
        v3_router_address=env("V3_ROUTER_ADDRESS"),
        v3_quoter_address=env("V3_QUOTER_ADDRESS"),
        v3_fee_tiers=_parse_fee_tiers(env("V3_FEE_TIERS", BSC_DEFAULT_V3_FEE_TIERS)),
        base_token_address=base_token_address,
        quote_token_address=quote_token_address,
        base_token_symbol=pick_str("base_token_symbol", env("BASE_TOKEN_SYMBOL", "BASE")),
        quote_token_symbol=pick_str("quote_token_symbol", env("QUOTE_TOKEN_SYMBOL", "QUOTE")),
        base_token_decimals=pick_int("base_token_decimals", int(env("BASE_TOKEN_DECIMALS", "18"))),
        quote_token_decimals=pick_int("quote_token_decimals", int(env("QUOTE_TOKEN_DECIMALS", "18"))),
        allowed_tokens=allowed_tokens,
        buy_amount_base=pick_float("buy_amount_base", float(env("BUY_AMOUNT_BASE", "10"))),
        sell_amount_quote=pick_float("sell_amount_quote", float(env("SELL_AMOUNT_QUOTE", "10"))),
        max_slippage_bps=pick_int("max_slippage_bps", int(env("MAX_SLIPPAGE_BPS", "80"))),
        max_gas_gwei=float(env("MAX_GAS_GWEI", "6")),
        cooldown_seconds=pick_int("cooldown_seconds", int(env("COOLDOWN_SECONDS", "120"))),
        daily_notional_limit_usd=pick_float(
            "daily_notional_limit_usd",
            float(env("DAILY_NOTIONAL_LIMIT_USD", "300")),
        ),
        state_file=env("STATE_FILE", "./data/state.json"),
        trade_log_file=env("TRADE_LOG_FILE", "./data/trades.ndjson"),
    )


def _resolve_trade_log_path() -> Path:
    _ensure_env_file()
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    raw = os.getenv("TRADE_LOG_FILE", "./data/trades.ndjson").strip() or "./data/trades.ndjson"
    p = Path(raw)
    if not p.is_absolute():
        p = APP_DIR / p
    return p


def _print_history(limit: int, as_json: bool = False, side: str = "all") -> None:
    log_path = _resolve_trade_log_path()
    if not log_path.exists():
        print(f"[history] no trade log file: {log_path}")
        return
    side_norm = str(side or "all").strip().lower()
    if side_norm not in {"all", "buy", "sell", "hold"}:
        side_norm = "all"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    max_rows = max(1, int(limit))
    rows = lines[-max_rows:] if lines else []
    filtered: list[dict[str, Any]] = []
    for raw in rows:
        try:
            item = json.loads(raw)
        except Exception:
            continue
        signal = item.get("signal") if isinstance(item.get("signal"), dict) else {}
        action = str(signal.get("action", "")).strip().lower()
        if side_norm == "all":
            if action not in {"buy", "sell"}:
                continue
        elif action != side_norm:
            continue
        filtered.append(item)
    if not filtered:
        print("[history] no records")
        return
    print(f"[history] showing {len(filtered)} rows from {log_path} (side={side_norm})")
    for item in filtered:
        if as_json:
            print(json.dumps(item, ensure_ascii=False))
            continue
        ts = str(item.get("ts", "-"))
        status = str(item.get("status", "-"))
        signal = item.get("signal") if isinstance(item.get("signal"), dict) else {}
        action = str(signal.get("action", "-")).upper()
        reason = str(item.get("reason") or signal.get("reason") or "")
        tx_hash = ""
        result = item.get("result")
        if isinstance(result, dict):
            tx_hash = str(result.get("tx_hash", ""))
        parts = [ts, status, action]
        if reason:
            parts.append(reason)
        if tx_hash:
            parts.append(f"tx={tx_hash}")
        print(" | ".join(parts))


def _wait_for_menu_return(stop_event: threading.Event) -> None:
    try:
        input("\n[loop] Press Enter to return to menu / 엔터를 누르면 메뉴로 돌아갑니다: ")
    except Exception:
        pass
    stop_event.set()


def run_bot(once: bool = False, interactive_loop: bool = False) -> None:
    cfg = build_config()
    bot = SwapBot(cfg)
    print(
        f"[start] paper_mode={cfg.paper_mode} poll={cfg.poll_seconds}s "
        f"signal={cfg.signal_url} config={cfg.bot_config_url} "
        f"v2={cfg.router_address} v3={cfg.v3_router_address} fees={cfg.v3_fee_tiers}"
    )
    stop_event: threading.Event | None = None
    if interactive_loop and not once and sys.stdin.isatty():
        stop_event = threading.Event()
        threading.Thread(
            target=_wait_for_menu_return,
            args=(stop_event,),
            daemon=True,
        ).start()
    if once:
        try:
            bot.run_once()
        except Exception as e:
            print(f"[error] {e}")
            bot._append_log({"status": "error", "error": str(e)})
        return

    while True:
        if stop_event and stop_event.is_set():
            print("[loop] menu return requested / 메뉴 복귀 요청됨")
            break
        try:
            bot.run_once()
        except Exception as e:
            print(f"[error] {e}")
            bot._append_log({"status": "error", "error": str(e)})
        slept = 0.0
        while slept < float(cfg.poll_seconds):
            if stop_event and stop_event.is_set():
                break
            step = min(0.2, float(cfg.poll_seconds) - slept)
            if step <= 0:
                break
            time.sleep(step)
            slept += step
        if stop_event and stop_event.is_set():
            print("[loop] stopped and back to menu / 루프 중지 후 메뉴로 복귀")
            break


def _interactive_menu() -> tuple[str, bool, int, bool, str]:
    while True:
        mode_name = _current_mode_name()
        print("")
        print(f"[menu] Select command / 실행 옵션 선택 (mode={mode_name})")
        print("1) Start loop / 기본 루프 실행")
        print("2) Start once / 1회 실행")
        print("3) History / 거래내역 보기")
        print("4) Change mode / 모드 변경 (paper/live)")
        print("5) Set wallet key / 프라이빗 키 입력")
        print("6) Change bot token / 봇토큰 변경")
        print(f"7) Change NEAR API key / NEAR API 키 변경 ({_near_api_status_line()})")
        print("8) Exit / 종료")
        raw = input("Choose (1/2/3/4/5/6/7/8, default 1): ").strip()
        if raw == "8":
            return ("exit", False, 50, False, "all")
        if raw == "7":
            try:
                _set_near_api_key_interactive()
            except Exception as e:
                print(f"[menu] NEAR API key update failed / NEAR API 키 변경 실패: {e}")
            continue
        if raw == "2":
            return ("start", True, 50, False, "all")
        if raw == "3":
            limit_raw = input("History limit (default 50): ").strip()
            side_raw = input("Side filter (all/buy/sell/hold, default all): ").strip().lower()
            as_json_raw = input("JSON output? (y/N): ").strip().lower()
            try:
                limit = int(limit_raw) if limit_raw else 50
            except Exception:
                limit = 50
            side = side_raw if side_raw in {"all", "buy", "sell", "hold"} else "all"
            as_json = as_json_raw in {"y", "yes", "1", "true"}
            return ("history", False, max(1, limit), as_json, side)
        if raw == "4":
            mode_raw = input("Mode (paper/live): ").strip().lower()
            if mode_raw not in {"paper", "live"}:
                print("[menu] invalid mode / 잘못된 모드 입력")
                continue
            _set_mode(mode_raw)
            continue
        if raw == "5":
            try:
                _set_wallet_credentials_interactive()
            except Exception as e:
                print(f"[menu] wallet setup failed / 지갑 설정 실패: {e}")
            continue
        if raw == "6":
            try:
                _set_signal_token_interactive()
            except Exception as e:
                print(f"[menu] bot token update failed / 봇토큰 변경 실패: {e}")
            continue
        return ("start", False, 50, False, "all")


def main() -> None:
    parser = argparse.ArgumentParser(description="User-hosted swap bot")
    parser.add_argument(
        "cmd",
        nargs="?",
        choices=["start", "history"],
        help="start bot loop or show history",
    )
    parser.add_argument("--once", action="store_true", help="run only one cycle")
    parser.add_argument("--limit", type=int, default=50, help="number of rows to show")
    parser.add_argument("--json", action="store_true", help="print raw json lines")
    parser.add_argument(
        "--side",
        choices=["all", "buy", "sell", "hold"],
        default="all",
        help="history filter by side (all=buy+sell legacy)",
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        help="set PAPER_MODE before command",
    )
    parser.add_argument(
        "--set-bot-token",
        nargs="?",
        const="",
        help="set SIGNAL_TOKEN (when value omitted, prompt in tty)",
    )
    parser.add_argument(
        "--set-near-api-key",
        nargs="?",
        const="",
        help="set NEAR_API_KEY (when value omitted, prompt in tty)",
    )

    args = parser.parse_args()
    cmd = args.cmd
    once = bool(args.once)
    limit = max(1, int(args.limit))
    as_json = bool(args.json)
    side = str(args.side or "all")
    mode = args.mode
    set_bot_token = args.set_bot_token
    set_near_api_key = args.set_near_api_key

    if set_bot_token is not None:
        _set_signal_token_interactive(set_bot_token)
    if set_near_api_key is not None:
        _set_near_api_key_interactive(set_near_api_key)
    if mode:
        _set_mode(mode)

    if not cmd and sys.stdin.isatty():
        while True:
            cmd_i, once_i, limit_i, as_json_i, side_i = _interactive_menu()
            if cmd_i == "exit":
                print("[menu] bye / 종료")
                return
            if cmd_i == "history":
                _print_history(limit=limit_i, as_json=as_json_i, side=side_i)
                continue
            run_bot(once=once_i, interactive_loop=True)
        return

    if not cmd:
        cmd = "start"
    if cmd == "history":
        _print_history(limit=limit, as_json=as_json, side=side)
        return
    run_bot(once=once)


if __name__ == "__main__":
    main()
