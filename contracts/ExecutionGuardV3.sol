// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice PancakeSwap v3 router subset (BSC)
interface IPancakeV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

interface IWBNB is IERC20 {
    function deposit() external payable;
    function withdraw(uint256 wad) external;
}

/// @notice User-signed intent guard for auto-bot execution on Pancake v3.
/// @dev Bot executes only when it has a valid EIP-712 signature from user.
contract ExecutionGuardV3 {
    string public constant NAME = "KyunSwapExecutionGuardV3";
    string public constant VERSION = "1";

    bytes32 private constant EIP712_DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 private constant V3_INTENT_TYPEHASH = keccak256(
        "V3Intent(address owner,address tokenIn,address tokenOut,uint24 fee,address recipient,uint256 amountIn,uint256 amountOutMin,uint256 deadline,uint256 nonce,bool fromNative,bool toNative)"
    );
    uint256 private constant SECP256K1N_DIV_2 =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;

    IPancakeV3Router public immutable router;
    IWBNB public immutable wbnb;
    address public owner;

    mapping(address => bool) public executors;
    mapping(bytes32 => bool) public usedDigests;

    struct V3Intent {
        address owner;
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMin;
        uint256 deadline;
        uint256 nonce;
        bool fromNative;
        bool toNative;
    }

    event ExecutorUpdated(address indexed executor, bool allowed);
    event IntentCanceled(bytes32 indexed digest, address indexed owner);
    event IntentExecuted(
        bytes32 indexed digest,
        address indexed signer,
        address indexed executor,
        address tokenIn,
        address tokenOut,
        uint24 fee,
        uint256 amountIn,
        uint256 amountOut
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyExecutor() {
        require(msg.sender == owner || executors[msg.sender], "not executor");
        _;
    }

    constructor(address router_, address wbnb_) {
        require(router_ != address(0) && wbnb_ != address(0), "zero addr");
        owner = msg.sender;
        router = IPancakeV3Router(router_);
        wbnb = IWBNB(wbnb_);
    }

    receive() external payable {}

    function setExecutor(address executor, bool allowed) external onlyOwner {
        executors[executor] = allowed;
        emit ExecutorUpdated(executor, allowed);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        owner = newOwner;
    }

    /// @notice User-driven cancel: caller must be intent owner.
    function cancelIntentByOwner(V3Intent calldata intent) external {
        require(msg.sender == intent.owner, "not intent owner");
        bytes32 digest = _hashTypedDataV4(_hashIntentStruct(intent));
        require(!usedDigests[digest], "already used");
        usedDigests[digest] = true;
        emit IntentCanceled(digest, msg.sender);
    }

    /// @notice Emergency cancel by digest (contract owner only).
    function cancelIntent(bytes32 digest) external {
        require(msg.sender == owner, "not owner");
        require(!usedDigests[digest], "already used");
        usedDigests[digest] = true;
        emit IntentCanceled(digest, msg.sender);
    }

    function hashIntent(V3Intent calldata intent) external view returns (bytes32) {
        return _hashTypedDataV4(_hashIntentStruct(intent));
    }

    /// @notice Execute signed intent. Bot should call this function.
    function executeV3(V3Intent calldata intent, bytes calldata signature)
        external
        payable
        onlyExecutor
        returns (uint256 amountOut)
    {
        require(intent.owner != address(0), "bad owner");
        require(intent.amountIn > 0, "bad amountIn");
        require(intent.amountOutMin > 0, "bad amountOutMin");
        require(intent.deadline >= block.timestamp, "intent expired");
        require(intent.recipient != address(0), "bad recipient");

        if (intent.fromNative) {
            require(intent.tokenIn == address(wbnb), "native in requires WBNB tokenIn");
            require(msg.value == intent.amountIn, "native value mismatch");
        } else {
            require(msg.value == 0, "no msg.value");
        }
        if (intent.toNative) {
            require(intent.tokenOut == address(wbnb), "native out requires WBNB tokenOut");
        }

        bytes32 digest = _hashTypedDataV4(_hashIntentStruct(intent));
        require(!usedDigests[digest], "intent used");
        address signer = _recoverSigner(digest, signature);
        require(signer == intent.owner, "bad signature");
        usedDigests[digest] = true;

        if (intent.fromNative) {
            wbnb.deposit{value: intent.amountIn}();
            _safeApprove(address(wbnb), address(router), intent.amountIn);
        } else {
            require(
                IERC20(intent.tokenIn).transferFrom(intent.owner, address(this), intent.amountIn),
                "transferFrom fail"
            );
            _safeApprove(intent.tokenIn, address(router), intent.amountIn);
        }

        address actualRecipient = intent.toNative ? address(this) : intent.recipient;
        IPancakeV3Router.ExactInputSingleParams memory params = IPancakeV3Router.ExactInputSingleParams({
            tokenIn: intent.tokenIn,
            tokenOut: intent.tokenOut,
            fee: intent.fee,
            recipient: actualRecipient,
            amountIn: intent.amountIn,
            amountOutMinimum: intent.amountOutMin,
            sqrtPriceLimitX96: 0
        });

        amountOut = router.exactInputSingle(params);

        if (intent.toNative) {
            wbnb.withdraw(amountOut);
            (bool ok, ) = payable(intent.recipient).call{value: amountOut}("");
            require(ok, "native transfer fail");
        }

        _safeApprove(intent.tokenIn, address(router), 0);

        emit IntentExecuted(
            digest,
            signer,
            msg.sender,
            intent.tokenIn,
            intent.tokenOut,
            intent.fee,
            intent.amountIn,
            amountOut
        );
    }

    function _safeApprove(address token, address spender, uint256 amount) private {
        require(IERC20(token).approve(spender, amount), "approve fail");
    }

    function _hashIntentStruct(V3Intent calldata intent) private pure returns (bytes32) {
        return keccak256(
            abi.encode(
                V3_INTENT_TYPEHASH,
                intent.owner,
                intent.tokenIn,
                intent.tokenOut,
                intent.fee,
                intent.recipient,
                intent.amountIn,
                intent.amountOutMin,
                intent.deadline,
                intent.nonce,
                intent.fromNative,
                intent.toNative
            )
        );
    }

    function _domainSeparatorV4() private view returns (bytes32) {
        return keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes(NAME)),
                keccak256(bytes(VERSION)),
                block.chainid,
                address(this)
            )
        );
    }

    function _hashTypedDataV4(bytes32 structHash) private view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", _domainSeparatorV4(), structHash));
    }

    function _recoverSigner(bytes32 digest, bytes calldata signature) private pure returns (address) {
        require(signature.length == 65, "bad sig len");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v < 27) v += 27;
        require(v == 27 || v == 28, "bad v");
        require(uint256(s) <= SECP256K1N_DIV_2, "bad s");
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "zero signer");
        return signer;
    }

    function sweepToken(address token, address to, uint256 amount) external onlyOwner {
        require(token != address(0) && to != address(0), "zero addr");
        require(IERC20(token).transfer(to, amount), "token transfer fail");
    }

    function sweepNative(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "zero addr");
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "native transfer fail");
    }
}
