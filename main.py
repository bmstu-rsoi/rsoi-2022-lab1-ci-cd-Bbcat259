import os
import sys
import psycopg2
import flask
import json

from urllib.request import Request
from flask import abort
from dataclasses import dataclass
from typing import Dict, List, Union

conn = psycopg2.connect(dbname='d3du8791pe6p5s', user='jzbgjnwqfgybsp', 
                        password='d0c1361e937da4f78d9fbebb3b4c7d17108e1bfb3829f81f613a00a189b9501e', host='ec2-44-210-36-247.compute-1.amazonaws.com')

cursor = conn.cursor()

app = flask.Flask(__name__)

class ApiMessage:
    def toJSON(obj):
        return json.dumps(obj, separators=(',', ':'),
                          default=cleanNones)

def cleanNones(o):
    return {k: v for k,
            v in o.__dict__.items() if v is not None}

def arrToJson(arr: List[ApiMessage]):
    return json.dumps([cleanNones(e) for e in arr], separators=(',', ':'))

def parseInt32(s: str):
    try:
        val = int(s)
    except:
        return None
    return val

@dataclass
class PersonRequest(ApiMessage):
    name: str
    age: Union[int, None]
    address: Union[str, None]
    work: Union[str, None]

def parsePersonRequest(request: Request) -> Union[PersonRequest, None]:
    if not request.is_json:
        return None
    if request.json.get("name", None) == None:
        return None
    return PersonRequest(
        name=request.json.get("name"),
        age=request.json.get("age"),
        address=request.json.get("address"),
        work=request.json.get("work"),
    )

@dataclass
class PersonResponse(ApiMessage):
    id: int
    name: str
    age: Union[int, None]
    address: Union[str, None]
    work: Union[str, None]

@dataclass
class ErrorResponse(ApiMessage):
    msg: str

@dataclass
class ValidationErrorResponse(ApiMessage):
    msg: str
    errors: Dict[str, str]

def getPersons() -> List[PersonResponse]:
    cursor.execute('SELECT id, name, age, address, work FROM persons_lab1')
    persons_data = [PersonResponse(*e) for e in cursor]
    return persons_data

# работает 
def getOnePerson(id: int) -> Union[PersonResponse, None]:
    cursor.execute(
        'SELECT id, name, age, address, work FROM persons_lab1 WHERE id = %s', (id,))
    person_data = cursor.fetchone()
    if person_data != None:
        return PersonResponse(*person_data)
    else:
        return None

def createNewPerson(person: PersonRequest) -> int:
    cursor.execute('INSERT INTO persons_lab1(id, name, age, address, work)' +
                'VALUES (DEFAULT, %s, %s, %s, %s)' +
                'RETURNING id',
                (person.name, person.age, person.address, person.work))
    conn.commit()
    row = cursor.fetchone()
    return row[0]

def removePerson(id: int):
    cursor.execute('DELETE FROM persons_lab1 WHERE id = %s', (id,))
    conn.commit()

def patchPerson(id: int, person: PersonRequest) -> Union[PersonResponse, None]:
    params = [person.name]
    if person.age != None:
        params.append(person.age)
    if person.address != None:
        params.append(person.address)
    if person.work != None:
        params.append(person.work)
    params.append(id)
    cursor.execute('UPDATE persons_lab1 SET name = %s' +
                    (', age = %s' if person.age != None else '') +
                    (', address = %s' if person.address != None else '') +
                    (', work = %s' if person.work != None else '') +
                    'WHERE id = %s', params)
    conn.commit()

    return getOnePerson(id)

@app.route('/api/v1/persons', methods=['GET', 'POST'])
def personsRoute():
    if flask.request.method == 'GET':
        persons = getPersons()
        resp = flask.Response(arrToJson(persons), status = 200)
        resp.headers['Content-Type'] = 'application/json'
        return resp

    else:
        personRequest = parsePersonRequest(flask.request)
        if personRequest == None:
            abort(400)

        newId = createNewPerson(personRequest)
        resp = flask.Response('', status = 201)
        resp.headers['Location'] = f'/api/v1/persons/{newId}'
        return resp


@app.route('/api/v1/persons/<id>', methods=['GET', 'PATCH', 'DELETE'])
def personRoute(id):
    int_id = parseInt32(id)

    if flask.request.method == 'GET':
        person = getOnePerson(int_id)
        if person != None:
            resp = flask.Response(person.toJSON(), status = '200')
            resp.headers['Content-Type'] = 'application/json'
            return resp
        

    elif flask.request.method == 'PATCH':
        personRequest = parsePersonRequest(flask.request)
        if personRequest == None:
            resp = flask.Response('', status = '404')
            return resp

        person = patchPerson(int_id, personRequest)
        if person != None:
            resp = flask.Response(person.toJSON(), status = '200')
            resp.headers['Content-Type'] = 'application/json'
            return resp

    else:
        removePerson(int_id)
        return flask.Response('', status = '204')



port = 8080
herokuPort = os.environ.get('PORT')
if herokuPort != None:
    port = herokuPort
if len(sys.argv) > 1:
    port = int(sys.argv[1])

app.run(host="0.0.0.0", port=port)