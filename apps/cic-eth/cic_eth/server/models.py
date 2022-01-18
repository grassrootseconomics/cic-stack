from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    block_number: Optional[int] = Field(None, example=24531)
    date_checked: Optional[str] = Field(
        None, example='2021-11-12T09:36:40.725296')
    date_created: Optional[str] = Field(
        None, example='2021-11-12T09:36:40.131292')
    date_updated: Optional[str] = Field(
        None, example='2021-11-12T09:36:40.131292')
    destination_token: Optional[str] = Field(
        None, example=365185044137427460620354810422988491181438940190
    )
    destination_token_decimals: Optional[int] = Field(None, example=6)
    destination_token_symbol: Optional[str] = Field(None, example='COFE')
    from_value: Optional[int] = Field(None, example=100000000)
    hash: Optional[str] = Field(
        None,
        example=90380195350511178677041624165156640995490505896556680958001954705731707874291,
    )
    nonce: Optional[int] = Field(None, example=1)
    recipient: Optional[str] = Field(
        None, example='872e1ec9d499b242ebfcfd0a279a4c3e0cd472c0'
    )
    sender: Optional[str] = Field(
        None, example='1a92b05e0b880127a4c26ac0f68a52df3ac6b89d'
    )
    signed_tx: Optional[str] = Field(
        None,
        example=1601943273486236942256143665779318355236220334071247753507187634376562549990085710958441113013370129915441072693447256942510246386178938683325073160349857879326297351587330623503997011254644396580777843154770873208185332563272343361515226115860084201932230246018679661802320007832375955345977725551120479084062615799940692628221555193198194825737613358738414884130187144700126061702642574663703095161159219410608270,
    )
    source_token: Optional[str] = Field(
        None, example=365185044137427460620354810422988491181438940190
    )
    source_token_decimals: Optional[int] = Field(None, example=6)
    source_token_symbol: Optional[str] = Field(None, example='COFE')
    status: Optional[str] = Field(None, example='SUCCESS')
    status_code: Optional[int] = Field(None, example=4104)
    timestamp: Optional[int] = Field(None, example=1636709800)
    to_value: Optional[int] = Field(None, example=100000000)
    tx_hash: Optional[str] = Field(
        None,
        example=90380195350511178677041624165156640995490505896556680958001954705731707874291,
    )
    tx_index: Optional[int] = Field(None, example=0)


class DefaultToken(BaseModel):
    symbol: Optional[str] = Field(None, description='Token Symbol')
    address: Optional[str] = Field(None, description='Token Address')
    name: Optional[str] = Field(None, description='Token Name')
    decimals: Optional[int] = Field(None, description='Decimals')


class TokenBalance(BaseModel):
    address: Optional[str] = None
    converters: Optional[List[str]] = None
    balance_network: Optional[int] = None
    balance_incoming: Optional[int] = None
    balance_outgoing: Optional[int] = None
    balance_available: Optional[int] = None


class Token(BaseModel):
    decimals: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None
    symbol: Optional[str] = None
    proofs: Optional[List[str]] = None
    converters: Optional[List[str]] = None
    proofs_with_signers: Optional[List[Proof]] = None

    @staticmethod
    def new(data: List[dict]) -> Token:
        proofs_with_signers = [{"proof": proof, "signers": signers} for (proof, signers) in data[1].items()]
        return Token(**data[0], proofs_with_signers=proofs_with_signers)


class Proof(BaseModel):
    proof: Optional[str] = None
    signers: Optional[List[str]] = None


Token.update_forward_refs()
