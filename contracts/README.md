# ExecutionGuardV3 (PancakeSwap v3)

This contract is a minimal on-chain guard for your existing user-hosted bot flow.

## What it does
- Uses user EIP-712 signature (`V3Intent`) as execution authority.
- Bot/keeper executes only via `executeV3(intent, sig)`.
- Prevents unsigned arbitrary swaps.
- Supports native BNB in/out through WBNB wrapping/unwrapping.

## Network
- BSC (chainId 56), Solidity contract.

## Constructor args
- `router_`: PancakeSwap v3 router (BSC mainnet commonly `0x1b81D678ffb9C0263b24A97847620C99d213eB14`)
- `wbnb_`: WBNB (`0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c`)

## Intent fields (EIP-712)
- `owner`: user wallet that signed
- `tokenIn`, `tokenOut`
- `fee`: v3 fee tier (e.g. 500 / 2500 / 10000)
- `recipient`: final recipient wallet
- `amountIn`, `amountOutMin`
- `deadline`, `nonce`
- `fromNative`, `toNative`

## Execution flow
1. `index.html` asks user wallet to sign typed data (intent).
2. Backend/bot stores `intent + signature`.
3. Bot calls `executeV3(intent, signature)` when strategy condition is met.
4. Contract verifies signature and executes Pancake v3 swap.

## Important notes
- For ERC20 input, user must approve `ExecutionGuardV3` contract in advance.
- User-side cancel: `cancelIntentByOwner(intent)`.
- Owner emergency cancel: `cancelIntent(digest)`.
- `usedDigests` prevents replay.
