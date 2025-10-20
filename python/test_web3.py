from web3 import AsyncWeb3, AsyncHTTPProvider
print("Web3 version:", AsyncWeb3.__version__)
print("\nAvailable middleware in web3.middleware:")
import web3.middleware
for item in dir(web3.middleware):
    if not item.startswith('_'):
        print(f"- {item}")