import re
from staketaxcsv.algo.api_algoindexer import AlgoIndexerAPI
from staketaxcsv.algo.constants import ASSET_ID_ALGO
from staketaxcsv.algo.util import b64_decode_ascii

ASSET_LP_TOKENS = {
    "TM1POOL": {
        "pattern": re.compile(r"^Tinyman Pool (?P<asset1>\w*)-(?P<asset2>\w*)$"),
        "symbol": "TM"
    },
    "TMPOOL11": {
        "pattern": re.compile(r"^TinymanPool1.1 (?P<asset1>\w*)-(?P<asset2>\w*)$"),
        "symbol": "TM"
    },
    "TMPOOL2": {
        "pattern": re.compile(r"^TinymanPool2.0 (?P<asset1>\w*)-(?P<asset2>\w*)$"),
        "symbol": "TM"
    },
    "PLP": {
        "pattern": re.compile(r"^(?P<asset1>\w*)\/(?P<asset2>\w*) PACT LP Token$"),
        "symbol": "P"
    },
    "SIPLP": {
        "pattern": re.compile(r"^(?P<asset1>\w*)\/(?P<asset2>\w*) \[SI\] PACT LP TKN$"),
        "symbol": "P"
    },
    "AF-POOL": {
        "pattern": re.compile(r"^AF-POOL-(?P<asset1>\w*)-(?P<asset2>\w*)-\d+\.\d+BP$"),
        "symbol": "AF"
    },
    "HMBL1LT": {
        "pattern": re.compile(r"^HUMBLE LP - (?P<asset1>\w*)\/(?P<asset2>\w*)$"),
        "symbol": "HMB"
    },
    "HMBL2LT": {
        "pattern": re.compile(r"^HUMBLE LP - (?P<asset1>\w*)\/(?P<asset2>\w*)$"),
        "symbol": "HMB"
    },
}

ASSET_AF_LP_TOKENS = {
    658337286: ("USDC", "STBL"),
    659677515: ("USDT", "STBL"),
    659678778: ("USDT", "USDC"),
    841171328: ("STBL2", "USDC"),
    855717054: ("STBL2", "ALGO"),
    870151164: ("STBL2", "goBTC"),
    870150187: ("STBL2", "goETH"),
    900924035: ("BANK", "STBL2"),
    919950894: ("ALGO", "USDC"),
    962367827: ("ALGO", "BANK"),
}


def _parse_asset(asset):
    if "name" in asset and "unit-name" in asset:
        return {key: asset[key] for key in ["name", "unit-name", "decimals"]}
    elif "name-b64" in asset and "unit-name-b64" in asset:
        return {
            "name": b64_decode_ascii(asset["name-b64"]),
            "unit-name": b64_decode_ascii(asset["unit-name-b64"]),
            "decimals": asset["decimals"]
        }
    else:
        return None


class Asset:
    asset_list = {
        ASSET_ID_ALGO: {
            "name": "Algorand",
            "unit-name": "ALGO",
            "decimals": 6,
        }
    }
    indexer = AlgoIndexerAPI()

    def __init__(self, id, amount=0):
        if id < 0:
            raise ValueError("Asset id must be greater than zero")
        if int(amount) < 0:
            raise ValueError("Asset amount cannot be negative")

        self._id = id
        if id in self.asset_list:
            params = self.asset_list[id]
        else:
            resp = self.indexer.get_asset(id)
            params = _parse_asset(resp)
            if params is not None:
                self.asset_list[id] = params
        if params is None:
            raise ValueError(f"Invalid asset: id {id}")
        self._decimals = params["decimals"]
        # Remove non-ascii characters from the name
        self._ticker = params["unit-name"].encode('ascii', 'ignore').decode('ascii')
        self._name = params["name"]
        self._uint_amount = int(amount)

    @classmethod
    def load_assets(cls, assets):
        for asset in assets:
            if "unit-name" in asset:
                id = asset["asset-id"]
                cls.asset_list[id] = {key: asset[key] for key in ["name", "unit-name", "decimals"]}

    @property
    def id(self):
        return self._id

    @property
    def amount(self):
        return float(self._uint_amount) / float(10 ** self._decimals)

    @property
    def uint_amount(self):
        return self._uint_amount

    @property
    def name(self):
        return self._name

    @property
    def ticker(self):
        return self._ticker

    @property
    def decimals(self):
        return self._decimals

    def __add__(self, other):
        if type(other) == int:
            if other < 0:
                raise ValueError("Amounts cannot be negative")
            return Asset(self._id, self._uint_amount + other)

        if not isinstance(other, Asset):
            raise TypeError("Invalid argument")

        if self._id != other.id:
            raise ValueError("Cannot add different assets")

        return Asset(self._id, self._uint_amount + other._uint_amount)

    def __iadd__(self, other):
        if type(other) == int:
            if other < 0:
                raise ValueError("Amounts cannot be negative")
            self._uint_amount += other
        else:
            if not isinstance(other, Asset):
                raise TypeError("Invalid argument")
            if self._id != other.id:
                raise ValueError("Cannot add different assets")
            self._uint_amount += other._uint_amount

        return self

    def __sub__(self, other):
        if type(other) == int:
            if other < 0:
                raise ValueError("Amounts cannot be negative")
            if self._uint_amount < other:
                raise ValueError("Asset amount cannot be negative")
            return Asset(self._id, self._uint_amount - other)

        if not isinstance(other, Asset):
            raise TypeError("Invalid argument")
        if self._id != other.id:
            raise ValueError("Cannot substruct different assets")
        if self._uint_amount < other._uint_amount:
            raise ValueError("Asset amount cannot be negative")

        return Asset(self._id, self._uint_amount - other._uint_amount)

    def __isub__(self, other):
        if type(other) == int:
            if other < 0:
                raise ValueError("Amounts cannot be negative")
            if self._uint_amount < other:
                raise ValueError("Asset amount cannot be negative")
            self._uint_amount -= other
        else:
            if not isinstance(other, Asset):
                raise TypeError("Invalid argument")
            if self._id != other.id:
                raise ValueError("Cannot substruct different assets")
            if self._uint_amount < other._uint_amount:
                raise ValueError("Asset amount cannot be negative")
            self._uint_amount -= other._uint_amount

        return self

    def __mul__(self, other):
        if not isinstance(other, (int, float)):
            raise TypeError("Invalid argument")
        if other < 0:
            raise ValueError("Asset amount cannot be negative")

        return Asset(self._id, self._uint_amount * other)

    def __float__(self):
        return self.amount

    def __str__(self):
        return "{{:.{}f}}".format(self.decimals).format(self.amount)

    def zero(self):
        return self._uint_amount == 0

    def is_lp_token(self):
        return self._ticker in ASSET_LP_TOKENS

    def get_lp_token_currency(self):
        if self._ticker == "AF-POOL":
            pattern = ASSET_LP_TOKENS[self._ticker]["pattern"]
            if self._id in ASSET_AF_LP_TOKENS:
                asset1 = ASSET_AF_LP_TOKENS[self._id][0]
                asset2 = ASSET_AF_LP_TOKENS[self._id][1]
            else:
                match = pattern.match(self._name)
                if not match:
                    return False

                asset1 = match.group("asset1")
                asset2 = match.group("asset2")

            symbol = ASSET_LP_TOKENS[self._ticker]["symbol"]

            return f"LP_{symbol}_{asset1}_{asset2}"

        elif self._ticker in ASSET_LP_TOKENS:
            pattern = ASSET_LP_TOKENS[self._ticker]["pattern"]
            match = pattern.match(self._name)
            if not match:
                return False

            symbol = ASSET_LP_TOKENS[self._ticker]["symbol"]
            asset1 = match.group("asset1")
            asset2 = match.group("asset2")

            return f"LP_{symbol}_{asset1}_{asset2}"

        return None


class Algo(Asset):
    def __init__(self, amount=0):
        super().__init__(0, amount)
