"""Pydantic schemas for all structured LLM outputs and tool validation."""

from pydantic import BaseModel, Field


class BidItem(BaseModel):
    """A single ingredient bid for the closed auction."""

    ingredient: str = Field(description="Name of the ingredient to bid on")
    bid: float = Field(gt=0, description="Price willing to pay per unit (must be > 0)")
    quantity: int = Field(gt=0, description="Number of units to purchase (must be > 0)")


class ClosedBidResponse(BaseModel):
    """Structured output for the closed-bid phase."""

    bids: list[BidItem] = Field(description="List of ingredient bids to submit")
    reasoning: str = Field(description="Brief explanation of the bidding strategy")


class MenuItem(BaseModel):
    """A single dish on the restaurant menu."""

    name: str = Field(description="Name of the dish")
    price: float = Field(ge=0, description="Price in Saldo (must be >= 0)")


class MenuUpdateResponse(BaseModel):
    """Structured output for menu updates during the speaking phase."""

    menu_items: list[MenuItem] = Field(description="List of dishes to publish on the menu")
