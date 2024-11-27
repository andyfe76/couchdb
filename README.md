# CouchDB connector and ORM

## Connector

### Set revision limits
    db.set_rev_limit(100)

    {
        "ok": true
    }


### Insert documents
    adrian = {
        "name": "Adrian James",
        "age": 30
    }

    daniela = {
        "name": "Daniela Claire",
        "age": 25
    }


    adrian = db.post(adrian)

    {
        "name": "Adrian James",
        "age": 30,
        "_id": "1f1c3ec423bf53e5241c8a549e02215d",
        "_rev": "1-1ee4abb2c1f7d4227a2963afd4f38f36"
    }

    daniela = db.post(daniela)

    {
        "name": "Daniela Claire",
        "age": 25,
        "_id": "1f1c3ec423bf53e5241c8a549e022add",
        "_rev": "1-8490d1baac0b8d37c58491b0b6722bf4"
    }


### Update a document
    adrian_id = adrian['_id']
    adrian = db.get(adrian_id)

    adrian['age'] = 21

    adrian = db.put(adrian)

    {
        "_id": "1f1c3ec423bf53e5241c8a549e02215d",
        "_rev": "2-79256d80f0107238a4ff356b632aa0c3",
        "name": "Adrian James",
        "age": 21
    }

### Find docs
docs = db.find({"age": {"$gte": 25}})

[
    {
        "_id": "1f1c3ec423bf53e5241c8a549e022add",
        "_rev": "1-8490d1baac0b8d37c58491b0b6722bf4",
        "name": "Daniela Claire",
        "age": 25
    }
]

### Bulk update
    adrian['location'] = "Bucharest"
    daniela['location'] = "Timisoara"

    docs = [adrian, daniela]
    adrian, daniela = db.bulk_update(docs)

    {
        "_id": "1f1c3ec423bf53e5241c8a549e02215d",
        "_rev": "3-ed23475d9c7182aae4fd17748ee438f5",
        "name": "Adrian James",
        "age": 21,
        "location": "Bucharest"
    }
    {
        "name": "Daniela Claire",
        "age": 25,
        "_id": "1f1c3ec423bf53e5241c8a549e022add",
        "_rev": "2-f5867a805d009ccd639cd281818b1291",
        "location": "Timisoara"
    }

### Delete the document
    db.delete(adrian)

### Get the deleted documents
    deleted_docs = db.deleted_docs()

    {
        "1f1c3ec423bf53e5241c8a549e02215d": [
            "4-f1efa6aadbe9006d03048485406f85bb"
        ]
    }

### Purge the deleted documents
    db.purge_all()

    deleted_docs = db.deleted_docs()

    {}

### Compact the database
db.compact()

### Clenaup the database
db.cleanup()

### Listen to changes
    from core import db

    doc = {"counter": 0}
    doc = db.post(doc)

    for change in db.changes({"_id": doc['_id']}):
        print(change)

    {
        "_id": "1f1c3ec423bf53e5241c8a549e02605a",
        "_rev": "2-078019c36aeca5065df83a205d0bd8de",
        "counter": 1
    }
    {
        "_id": "1f1c3ec423bf53e5241c8a549e02605a",
        "_rev": "3-6247beeb56b996ed7526b770568b1b23",
        "counter": 2
    }


## ORM

    from dataclasses import dataclass
    from orm import Orm

    @dataclass
    class Employee(Orm):
        name: str = None
        age: int = None
        is_active: bool = None

### Create a new employee
    employee = Employee(name="Adrian", age=30, is_active=True)
    employee.save()

    Employee(_id='db4b9866-08c6-466b-a988-621d11b3b1d5', _rev='1-d36bb232abb18893bf08854dcba9c5f7', name='Adrian', age=30, is_active=True)


### Load the employee
    employee = Employee.load(employee._id)
    employee.age = 31
    employee.save()

    Employee(_id='db4b9866-08c6-466b-a988-621d11b3b1d5', _rev='2-94ab3eec58bc950b05de67cc9ed2b147', name='Adrian', age=31, is_active=True)


### Search employees
    employees = Employee.find({"age": {"$gte": 30}})
    [Employee(_id='db4b9866-08c6-466b-a988-621d11b3b1d5', _rev='2-94ab3eec58bc950b05de67cc9ed2b147', name='Adrian', age=31, is_active=True)]
