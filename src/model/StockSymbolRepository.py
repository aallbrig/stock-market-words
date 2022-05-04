from src.model.StockSymbol import StockSymbol


class StockSymbolRepository:
    def get_all(self) -> list[StockSymbol]:
        raise NotImplementedError("Please Implement this method")
