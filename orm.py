from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from typing import Any, List, Dict, Union, get_origin, get_args
from dataclasses import dataclass, field, fields, is_dataclass, MISSING
from core import db

def serialize(model_instance: Any) -> Dict[str, Any]:
    """
    Serializes a dataclass instance into a dictionary, handling nested dataclasses,
    lists, dictionaries, and special types like Decimal and datetime.
    
    Args:
        model_instance (Any): The dataclass instance to serialize.
        
    Returns:
        Dict[str, Any]: A dictionary representation of the dataclass.
    """
    if not is_dataclass(model_instance):
        raise ValueError("serialize function expects a dataclass instance")
    
    def serialize_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif is_dataclass(value):
            return serialize(value)
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {key: serialize_value(val) for key, val in value.items()}
        else:
            return value

    serialized_data = {}
    model_fields = fields(model_instance)
    for field in model_fields:
        value = getattr(model_instance, field.name)
        serialized_data[field.name] = serialize_value(value)
    
    return serialized_data

def deserialize(model_class: Any, data: Dict[str, Any]) -> Any:
    """
    Deserializes a dictionary into a dataclass instance, handling nested dataclasses,
    lists, dictionaries, and special types like Decimal and datetime.
    
    Args:
        model_class (Any): The dataclass type to deserialize into.
        data (Dict[str, Any]): The dictionary containing the data.
        
    Returns:
        Any: An instance of `model_class` populated with the deserialized data.
    """
    if not is_dataclass(model_class):
        raise ValueError("deserialize function expects a dataclass type")
    
    def deserialize_value(field_type: Any, value: Any) -> Any:
        """
        Deserializes a single value based on the field type.
        """
        if value is None:
            return None
        
        origin = get_origin(field_type)
        args = get_args(field_type)
        
        # Handle Optional[T] (which is Union[T, NoneType])
        if origin is Union and type(None) in args:
            non_none_types = [arg for arg in args if arg is not type(None)]
            if len(non_none_types) == 1:
                return deserialize_value(non_none_types[0], value)
        
        # Handle List[T]
        if origin is list or origin is List:
            if not isinstance(value, list):
                raise TypeError(f"Expected list for field, got {type(value).__name__}")
            item_type = args[0] if args else Any
            return [deserialize_value(item_type, item) for item in value]
        
        # Handle Dict[K, V]
        if origin is dict or origin is Dict:
            if not isinstance(value, dict):
                raise TypeError(f"Expected dict for field, got {type(value).__name__}")
            key_type, val_type = args if args else (Any, Any)
            return {deserialize_value(key_type, k): deserialize_value(val_type, v) for k, v in value.items()}
        
        # Handle nested dataclasses
        if is_dataclass(field_type):
            if not isinstance(value, dict):
                raise TypeError(f"Expected dict for dataclass field, got {type(value).__name__}")
            return deserialize(field_type, value)
        
        # Handle special types
        if field_type is Decimal:
            return Decimal(value)
        elif field_type is datetime:
            return datetime.fromisoformat(value)
        elif field_type is int:
            return int(value)
        elif field_type is float:
            return float(value)
        elif field_type is str:
            return str(value)
        elif field_type is bool:
            return bool(value)
        
        # Fallback for other types
        return value
    
    deserialized_data = {}
    for field in fields(model_class):
        field_name = field.name
        field_type = field.type
        if field_name in data:
            raw_value = data[field_name]
            try:
                deserialized_data[field_name] = deserialize_value(field_type, raw_value)
            except Exception as e:
                raise ValueError(f"Error deserializing field '{field_name}': {e}") from e
        else:
            # Handle missing fields, possibly with default values
            if field.default is not MISSING:
                deserialized_data[field_name] = field.default
            elif field.default_factory is not MISSING:
                deserialized_data[field_name] = field.default_factory()
            else:
                deserialized_data[field_name] = None  # or raise an error
    
    return model_class(**deserialized_data)

@dataclass
class Orm():
    _id: str = field(default_factory=lambda: str(uuid4()))
    _rev: str = None

    @classmethod
    def load(cls, id) -> 'Orm':
        '''
        Load a class by its _id
        '''
        doc = db.get(id)
        if not doc:
            return None
        
        return deserialize(cls, doc)

    def save(self) -> 'Orm':
        '''
        Save the class instance
        '''
        doc = serialize(self)
        doc = db.put(doc)
        self._id, self._rev = doc['_id'], doc['_rev']
        return self
    
    def dict(self) -> Dict[str, Any]:
        '''
        Return the class instance as a dictionary
        '''
        return serialize(self)
    
    @classmethod
    def find(cls, query={}) -> List['Orm']:
        '''
        Find all documents that match the query

        query (dict): The query to match the documents
        '''

        docs = db.find(query=query)
        return [deserialize(cls, doc) for doc in docs]
    
    @classmethod
    def find_first(cls, query={}) -> 'Orm':
        '''
        Find the first document that matches the query
        
        query (dict): The query to match the document
        '''
        docs = cls.find(query)
        return docs[0] if len(docs) > 0 else None