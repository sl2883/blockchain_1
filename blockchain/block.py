from abc import ABC, abstractmethod  # We want to make Block an abstract class; either a PoW or PoA block
import blockchain
from blockchain import util
from blockchain.util import sha256_2_string, encode_as_str
import time
import persistent
from blockchain.util import nonempty_intersection


class Block(ABC, persistent.Persistent):

    def __init__(self, height, transactions, parent_hash, is_genesis=False, include_merkle_root=True):
        """ Creates a block template (unsealed).

        Args:
            height (int): height of the block in the chain (# of blocks between block and genesis).
            transactions (:obj:`list` of :obj:`Transaction`): ordered list of transactions in the block.
            parent_hash (str): the hash of the parent block in the blockchain.
            is_genesis (bool, optional): True only if the block is a genesis block.

        Attributes:
            parent_hash (str): the hash of the parent block in blockchain.
            height (int): height of the block in the chain (# of blocks between block and genesis).
            transactions (:obj:`list` of :obj:`Transaction`): ordered list of transactions in the block.
            timestamp (int): Unix timestamp of the block.
            target (int): Target value for the block's seal to be valid (different for each seal mechanism)
            is_genesis (bool): True only if the block is a genesis block (first block in the chain).
            merkle (str): Merkle hash of the list of transactions in a block, uniquely identifying the list.
            seal_data (int): Seal data for block (in PoW this is the nonce satisfying the PoW puzzle; in PoA, the signature of the authority").
            hash (str): Hex-encoded SHA256^2 hash of the block header (self.header()).
        """
        self.parent_hash = parent_hash
        self.height = height
        self.transactions = transactions
        self.timestamp = int(time.time())
        self.target = self.calculate_appropriate_target()
        self.is_genesis = is_genesis

        if include_merkle_root:
            self.merkle = self.calculate_merkle_root()
        else:
            self.merkle = sha256_2_string("".join([str(x) for x in self.transactions]))

        self.seal_data = 0  # temporarily set seal_data to 0
        self.hash = self.calculate_hash()  # keep track of hash for caching purposes

    def two_strings_to_merkle_hash(self, str1, str2):
        return sha256_2_string(str1 + str2)

    def list_to_merkle_hash(self, list1):
        if len(list1) == 0:
            return sha256_2_string("")
        elif len(list1) == 1:
            return sha256_2_string(str(list1[0]))
        else:
            first_list = list1[0:int(len(list1)/2)]
            second_list = list1[int(len(list1)/2):]
            return sha256_2_string(self.list_to_merkle_hash(first_list) + self.list_to_merkle_hash(second_list))

    def calculate_merkle_root(self):
        """ Gets the Merkle root hash for a given list of transactions.

        This method is incomplete!  Right now, it only hashes the
        transactions together, which does not enable the same type
        of lite client support a true Merkle hash would.

        Follow the description in the problem sheet to calculte the merkle root. 
        If there is no transaction, return SHA256(SHA256("")).
        If there is only one transaction, the merkle root is the transaction hash.
        For simplicity, when computing H(AB) = SHA256(SHA256(H(A) + H(B))), directly double-hash the hex string of H(A) concatenated with H(B).
        E.g., H(A) = 0x10, H(B) = 0xff, then H(AB) = SHA256(SHA256("10ff")).

        Returns:
            str: Merkle root hash of the list of transactions in a block, uniquely identifying the list.
        # Placeholder for (1c)
        all_txs_as_string = "".join([str(x) for x in self.transactions])

        return sha256_2_string(all_txs_as_string)
        """
        merkle = self.list_to_merkle_hash(self.transactions)
        return merkle

    def unsealed_header(self):
        """ Computes the header string of a block (the component that is sealed by mining).

        Returns:
            str: String representation of the block header without the seal.
        """
        return encode_as_str([self.height, self.timestamp, self.target, self.parent_hash, self.is_genesis, self.merkle],
                             sep='`')

    def header(self):
        """ Computes the full header string of a block after mining (includes the seal).

        Returns:
            str: String representation of the block header.
        """
        return encode_as_str([self.unsealed_header(), self.seal_data], sep='`')

    def calculate_hash(self):
        """ Get the SHA256^2 hash of the block header.

        Returns:
            str: Hex-encoded SHA256^2 hash of self.header()
        """
        return sha256_2_string(str(self.header()))

    def __repr__(self):
        """ Get a full representation of a block as string, for debugging purposes; includes all transactions.

        Returns:
            str: Full and unique representation of a block and its transactions.
        """
        return encode_as_str([self.header(), "!".join([str(tx) for tx in self.transactions])], sep="`")

    def set_seal_data(self, seal_data):
        """ Adds seal data to a block, recomputing the block's hash for its changed header representation.
        This method should never be called after a block is added to the blockchain!

        Args:
            seal_data (int): The seal data to set.
        """
        self.seal_data = seal_data
        self.hash = self.calculate_hash()

    def is_tx_present(self, tx):
        for transaction in self.transactions:
            if tx.hash == transaction.hash:
                return True
        return False

    def is_inp_ref_present(self, inp_ref):
        for transaction in self.transactions:
            for tx_inp_ref in transaction.input_refs:
                if tx_inp_ref == inp_ref:
                    return True
        return False

    def is_valid(self):
        """ Check whether block is fully valid according to block rules.

        Includes checking for no double spend, that all transactions are valid, that all header fields are correctly
        computed, etc.

        Returns:
            bool, str: True if block is valid, False otherwise plus an error or success message.
        """

        chain = blockchain.chain  # This object of type Blockchain may be useful

        # Placeholder for (1a)

        # (checks that apply to all blocks)

        # Check that Merkle root calculation is consistent with transactions in block (use the calculate_merkle_root function) [test_rejects_invalid_merkle]
        # On failure: return False, "Merkle root failed to match"
        if self.calculate_merkle_root() != self.merkle:
            return False, "Merkle root failed to match"

        # Check that block.hash is correctly calculated [test_rejects_invalid_hash]
        # On failure: return False, "Hash failed to match"
        if self.hash != sha256_2_string(str(self.header())):
            return False, "Hash failed to match"

        # Check that there are at most 900 transactions in the block [test_rejects_too_many_txs]
        # On failure: return False, "Too many transactions"
        if len(self.transactions) > 900:
            return False, "Too many transactions"

        # (checks that apply to genesis block)
        # Check that height is 0 and parent_hash is "genesis" [test_invalid_genesis]
        # On failure: return False, "Invalid genesis"
        if self.is_genesis:
            if self.height != 0 or self.parent_hash != "genesis" or not self.seal_is_valid():
                return False, "Invalid genesis"
        else:
            # (checks that apply only to non-genesis blocks)
            # Check that parent exists (you may find chain.blocks helpful) [test_nonexistent_parent]
            # On failure: return False, "Nonexistent parent"
            if chain.blocks.get(self.parent_hash) is None:
                return False, "Nonexistent parent"

            # Check that height is correct w.r.t. parent height [test_bad_height]
            # On failure: return False, "Invalid height"
            parent = chain.blocks.get(self.parent_hash)
            if self.height != parent.height + 1:
                return False, "Invalid height"

            # Check that timestamp is non-decreasing [test_bad_timestamp]
            # On failure: return False, "Invalid timestamp"
            if self.timestamp < parent.timestamp:
                return False, "Invalid timestamp"

            # Check that seal is correctly computed and satisfies "target" requirements; use the provided seal_is_valid method [test_bad_seal]
            # On failure: return False, "Invalid seal"
            if not self.seal_is_valid():
                return False, "Invalid seal"

            # Check that all transactions within are valid (use tx.is_valid) [test_malformed_txs]
            # On failure: return False, "Malformed transaction included"
            for tx in self.transactions:
                if not tx.is_valid():
                    return False, "Malformed transaction included"

            # If above works, this should work?
            # if any([x.is_valid() for x in self.transactions]) is False:
            #    return False, "Malformed transaction included"

            block_inp_user = {}
            block_tx_out_inp_user = {}
            block_tx_out_out_user = {}

            block_tx_inp_receivers = {}
            # Check that for every transaction
            for tx in self.transactions:

                for output in tx.outputs:
                    block_tx_out_inp_user[output.sender] = output.sender
                    block_tx_out_out_user[output.receiver] = output.receiver

                # the transaction has not already been included on a block on the same blockchain as this block [test_double_tx_inclusion_same_chain]
                # (or twice in this block; you will have to check this manually) [test_double_tx_inclusion_same_block]
                # (you may find chain.get_chain_ending_with and chain.blocks_containing_tx and util.nonempty_intersection useful)
                # On failure: return False, "Double transaction inclusion"

                current_block = chain.blocks.get(self.parent_hash)

                if current_block:
                    trans_in_parent = False
                    while current_block is not None:
                        tx_to_check = current_block.is_tx_present(tx)
                        if tx_to_check:
                            return False, "Double transaction inclusion"
                        current_block = chain.blocks.get(current_block.parent_hash)

                tx_count = 0
                for tx_in_block in self.transactions:
                    if tx_in_block.hash == tx.hash:
                        tx_count = tx_count + 1

                if tx_count > 1:
                    return False, "Double transaction inclusion"

                # for every input ref in the tx
                input_ref_transaction = {}

                total_input = 0

                for input_ref in tx.input_refs:

                    # (you may find the string split method for parsing the input into its components)
                    tx_hash, list_index_of_output = input_ref.split(':')

                    # each input_ref is valid (aka corresponding transaction can be looked up in its holding transaction) [test_failed_input_lookup]
                    # (you may find chain.all_transactions useful here)
                    # On failure: return False, "Required output not found"
                    tx_temp = chain.all_transactions.get(tx_hash)

                    if tx_temp is None:
                        tx_exists = False
                        for tx_in in self.transactions:
                            if tx_in.hash == tx_hash:
                                tx_exists = True

                        if not tx_exists:
                            return False, "Required output not found"
                    else:
                        if int(list_index_of_output) > len(tx.input_refs):
                         return False, "Required output not found"

                        total_input = total_input + tx_temp.get_output_at(int(list_index_of_output))
                        tx_rec = tx_temp.get_receiver_at(int(list_index_of_output))
                        block_tx_inp_receivers[tx_rec] = tx_rec

                    # every input was sent to the same user (would normally carry a signature from this user; we leave this out for simplicity) [test_user_consistency]
                    # On failure: return False, "User inconsistencies"

                    # no input_ref has been spent in a previous block on this chain [test_doublespent_input_same_chain]
                    # (or in this block; you will have to check this manually) [test_doublespent_input_same_block]
                    # (you may find nonempty_intersection and chain.blocks_spending_input helpful here)
                    # On failure: return False, "Double-spent input"
                    current_block = chain.blocks.get(self.parent_hash)

                    while current_block.is_genesis is False:
                        if current_block.is_inp_ref_present(input_ref):
                            return False, "Double-spent input"
                        current_block = chain.blocks.get(current_block.parent_hash)

                    inp_ref_count = 0
                    for tx_in_block in self.transactions:
                        for tx_input_ref in tx_in_block.input_refs:
                            if input_ref == tx_input_ref:
                                inp_ref_count = inp_ref_count + 1

                    if inp_ref_count > 1:
                        return False, "Double-spent input"

                    # each input_ref points to a transaction on the same blockchain as this block [
                    # test_input_txs_on_chain] (or in this block; you will have to check this manually) [
                    # test_input_txs_in_block] (you may find chain.blocks_containing_tx.get and nonempty_intersection
                    # as above helpful) On failure: return False, "Input transaction not found"
                    current_block = chain.blocks.get(self.parent_hash)

                    if current_block:
                        trans_in_parent = False
                        while current_block is not None:
                            tx_to_check = chain.all_transactions.get(tx_hash)
                            if tx_to_check and current_block.is_tx_present(tx_to_check):
                                trans_in_parent = True
                            current_block = chain.blocks.get(current_block.parent_hash)

                        if not trans_in_parent:
                            for tx_in_block in self.transactions:
                                if tx_in_block.hash == tx_hash:
                                    trans_in_parent = True

                        if not trans_in_parent:
                            return False, "Input transaction not found"




                # for every output in the tx
                # every output was sent from the same user (would normally carry a signature from this user; we leave this out for simplicity)
                # (this MUST be the same user as the outputs are locked to above) [test_user_consistency]
                # On failure: return False, "User inconsistencies"
                inp_users = {}
                for output in tx.outputs:
                    inp_users[output.sender] = output.sender

                total_output = tx.get_total_output()

                if len(inp_users) > 1:
                    return False, "User inconsistencies"

                if len(block_tx_inp_receivers) > 0 and len(block_tx_out_inp_user) > 0:
                    if len(block_tx_inp_receivers) > 1:
                        return False, "User inconsistencies"

                    user_received_inp = block_tx_inp_receivers.popitem()
                    user_sending_out = block_tx_out_inp_user.popitem()

                    if user_received_inp != user_sending_out:
                        return False, "User inconsistencies"


                if total_input < total_output:
                    return False, 'Creating money'

                # the sum of the input values is at least the sum of the output values (no money created out of thin air) [test_no_money_creation]

                # On failure: return False, "Creating money"

        return True, "All checks passed"

    # ( these just establish methods for subclasses to implement; no need to modify )
    @abstractmethod
    def get_weight(self):
        """ Should be implemented by subclasses; gives consensus weight of block. """
        pass

    @abstractmethod
    def calculate_appropriate_target(self):
        """ Should be implemented by subclasses; calculates correct target to use in block. """
        pass

    @abstractmethod
    def seal_is_valid(self):
        """ Should be implemented by subclasses; returns True iff the seal_data creates a valid seal on the block. """
        pass
