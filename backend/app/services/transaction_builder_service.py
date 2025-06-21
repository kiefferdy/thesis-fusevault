from typing import Dict, Any, Optional
from web3 import Web3
from eth_utils import to_checksum_address
import logging

logger = logging.getLogger(__name__)

class TransactionBuilderService:
    """Service for building unsigned blockchain transactions."""
    
    def __init__(self, web3: Web3, contract):
        self.web3 = web3
        self.contract = contract
    
    async def build_update_ipfs_transaction(
        self,
        asset_id: str,
        cid: str,
        from_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build unsigned transaction for updateIPFS.
        
        Args:
            asset_id: The asset ID to update
            cid: The IPFS CID to store
            from_address: The wallet address that will sign the transaction
            gas_limit: Optional gas limit override
            
        Returns:
            Dict containing transaction data or error information
        """
        try:
            from_address = to_checksum_address(from_address)
            nonce = self.web3.eth.get_transaction_count(from_address)
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            tx = self.contract.functions.updateIPFS(
                asset_id,
                cid
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit or 2000000,
                'chainId': self.web3.eth.chain_id
            })
            
            # Remove fields that will be added during signing
            tx.pop('maxFeePerGas', None)
            tx.pop('maxPriorityFeePerGas', None)
            
            logger.info(f"Built updateIPFS transaction for asset {asset_id} from {from_address}")
            
            return {
                "success": True,
                "transaction": tx,
                "estimated_gas": gas_limit or 2000000,
                "gas_price": gas_price,
                "function_name": "updateIPFS"
            }
            
        except Exception as e:
            logger.error(f"Error building updateIPFS transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_update_ipfs_for_transaction(
        self,
        owner_address: str,
        asset_id: str,
        cid: str,
        from_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build unsigned transaction for updateIPFSFor (delegation).
        
        Args:
            owner_address: The owner of the asset
            asset_id: The asset ID to update
            cid: The IPFS CID to store
            from_address: The delegate wallet address that will sign the transaction
            gas_limit: Optional gas limit override
            
        Returns:
            Dict containing transaction data or error information
        """
        try:
            from_address = to_checksum_address(from_address)
            owner_address = to_checksum_address(owner_address)
            nonce = self.web3.eth.get_transaction_count(from_address)
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            tx = self.contract.functions.updateIPFSFor(
                owner_address,
                asset_id,
                cid
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit or 2000000,
                'chainId': self.web3.eth.chain_id
            })
            
            # Remove fields that will be added during signing
            tx.pop('maxFeePerGas', None)
            tx.pop('maxPriorityFeePerGas', None)
            
            logger.info(f"Built updateIPFSFor transaction for asset {asset_id} from {from_address} for owner {owner_address}")
            
            return {
                "success": True,
                "transaction": tx,
                "estimated_gas": gas_limit or 2000000,
                "gas_price": gas_price,
                "function_name": "updateIPFSFor"
            }
            
        except Exception as e:
            logger.error(f"Error building updateIPFSFor transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_delete_asset_transaction(
        self,
        asset_id: str,
        from_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build unsigned transaction for deleteAsset.
        
        Args:
            asset_id: The asset ID to delete
            from_address: The wallet address that will sign the transaction
            gas_limit: Optional gas limit override
            
        Returns:
            Dict containing transaction data or error information
        """
        try:
            from_address = to_checksum_address(from_address)
            nonce = self.web3.eth.get_transaction_count(from_address)
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            tx = self.contract.functions.deleteAsset(asset_id).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit or 2000000,
                'chainId': self.web3.eth.chain_id
            })
            
            # Remove fields that will be added during signing
            tx.pop('maxFeePerGas', None)
            tx.pop('maxPriorityFeePerGas', None)
            
            logger.info(f"Built deleteAsset transaction for asset {asset_id} from {from_address}")
            
            return {
                "success": True,
                "transaction": tx,
                "estimated_gas": gas_limit or 2000000,
                "gas_price": gas_price,
                "function_name": "deleteAsset"
            }
            
        except Exception as e:
            logger.error(f"Error building deleteAsset transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_delete_asset_for_transaction(
        self,
        owner_address: str,
        asset_id: str,
        from_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build unsigned transaction for deleteAssetFor (delegation).
        
        Args:
            owner_address: The owner of the asset
            asset_id: The asset ID to delete
            from_address: The delegate wallet address that will sign the transaction
            gas_limit: Optional gas limit override
            
        Returns:
            Dict containing transaction data or error information
        """
        try:
            from_address = to_checksum_address(from_address)
            owner_address = to_checksum_address(owner_address)
            nonce = self.web3.eth.get_transaction_count(from_address)
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            tx = self.contract.functions.deleteAssetFor(
                owner_address,
                asset_id
            ).build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': gas_limit or 2000000,
                'chainId': self.web3.eth.chain_id
            })
            
            # Remove fields that will be added during signing
            tx.pop('maxFeePerGas', None)
            tx.pop('maxPriorityFeePerGas', None)
            
            logger.info(f"Built deleteAssetFor transaction for asset {asset_id} from {from_address} for owner {owner_address}")
            
            return {
                "success": True,
                "transaction": tx,
                "estimated_gas": gas_limit or 2000000,
                "gas_price": gas_price,
                "function_name": "deleteAssetFor"
            }
            
        except Exception as e:
            logger.error(f"Error building deleteAssetFor transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def estimate_gas(
        self,
        function_name: str,
        from_address: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Estimate gas for a transaction without building it.
        
        Args:
            function_name: Name of the contract function
            from_address: The wallet address that will sign the transaction
            **kwargs: Function-specific arguments
            
        Returns:
            Dict containing gas estimation or error information
        """
        try:
            from_address = to_checksum_address(from_address)
            
            if function_name == "updateIPFS":
                gas_estimate = self.contract.functions.updateIPFS(
                    kwargs['asset_id'],
                    kwargs['cid']
                ).estimate_gas({'from': from_address})
                
            elif function_name == "updateIPFSFor":
                owner_address = to_checksum_address(kwargs['owner_address'])
                gas_estimate = self.contract.functions.updateIPFSFor(
                    owner_address,
                    kwargs['asset_id'],
                    kwargs['cid']
                ).estimate_gas({'from': from_address})
                
            elif function_name == "deleteAsset":
                gas_estimate = self.contract.functions.deleteAsset(
                    kwargs['asset_id']
                ).estimate_gas({'from': from_address})
                
            elif function_name == "deleteAssetFor":
                owner_address = to_checksum_address(kwargs['owner_address'])
                gas_estimate = self.contract.functions.deleteAssetFor(
                    owner_address,
                    kwargs['asset_id']
                ).estimate_gas({'from': from_address})
                
            else:
                raise ValueError(f"Unknown function: {function_name}")
            
            gas_price = self.web3.eth.gas_price
            estimated_cost = gas_estimate * gas_price
            
            logger.info(f"Gas estimation for {function_name}: {gas_estimate} gas")
            
            return {
                "success": True,
                "gas_estimate": gas_estimate,
                "gas_price": gas_price,
                "estimated_cost_wei": estimated_cost,
                "estimated_cost_eth": self.web3.from_wei(estimated_cost, 'ether'),
                "function_name": function_name
            }
            
        except Exception as e:
            logger.error(f"Error estimating gas for {function_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def build_set_delegate_transaction(
        self,
        delegate_address: str,
        status: bool,
        from_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build unsigned transaction for setDelegate.
        
        Args:
            delegate_address: Address to delegate to
            status: True to delegate, False to revoke
            from_address: Address that will sign the transaction
            gas_limit: Optional gas limit override
            
        Returns:
            Dict with unsigned transaction data
        """
        try:
            # Validate addresses
            delegate_address = to_checksum_address(delegate_address)
            from_address = to_checksum_address(from_address)
            
            # Build the transaction
            function = self.contract.functions.setDelegate(delegate_address, status)
            
            # Estimate gas if not provided
            if not gas_limit:
                try:
                    gas_limit = function.estimate_gas({'from': from_address})
                    # Add 10% buffer
                    gas_limit = int(gas_limit * 1.1)
                except Exception as e:
                    logger.warning(f"Gas estimation failed, using default: {e}")
                    gas_limit = 150000
            
            # Get current gas price
            gas_price = self.web3.eth.gas_price
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(from_address)
            
            transaction = function.build_transaction({
                'from': from_address,
                'nonce': nonce,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': self.web3.eth.chain_id
            })
            
            # Remove 'from' field as it's not needed for signing
            transaction.pop('from', None)
            
            logger.info(
                f"Built setDelegate transaction: {delegate_address} "
                f"(status: {status}) for {from_address}"
            )
            
            return {
                "success": True,
                "transaction": transaction,
                "estimated_gas": gas_limit,
                "gas_price": gas_price,
                "function_name": "setDelegate"
            }
            
        except Exception as e:
            logger.error(f"Error building setDelegate transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }