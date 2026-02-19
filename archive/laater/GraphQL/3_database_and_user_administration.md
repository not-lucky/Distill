# Chapter 4: Database and user administration

## Select a page in the chapter

## Exercises in this chapter

**Chapter 4: Database and user administration**

> Note: You will not receive points for exercises in this chapter until you lock the chapter and a teacher reviews your answers.

- [Exercise 4.1: Phonebook database, step 1](/org/uh-cs/courses/full-stack-open-graphql/chapter-4#be23a471-1184-4015-ab92-e49a57224e3e)
- [Exercise 4.2: Phonebook database, step 2](/org/uh-cs/courses/full-stack-open-graphql/chapter-4#54a91234-4ab7-45f4-9dee-3843d5fe63bc)
- [Exercise 4.3: Phonebook database, step 3](/org/uh-cs/courses/full-stack-open-graphql/chapter-4#35bd63d2-d047-447d-a3e7-a3297242f1ca)
- [Exercise 4.4: Phonebook database, step 4](/org/uh-cs/courses/full-stack-open-graphql/chapter-4#b3d08725-5cfc-4237-b975-1c8517a60e92)
- [Exercise 4.5: Phonebook database, step 5](/org/uh-cs/courses/full-stack-open-graphql/chapter-4#2812cdb5-321b-4b12-8285-4c2a29a265fe)

## Refactoring the backend into modules

Before we start using a database, let's refactor the backend so that the code is divided into separate modules.

The GraphQL schema is moved to its own module, *schema.js*:

```graphql
const { gql } = require('@apollo/server')

const typeDefs = gql`
  type Address {
    street: String!
    city: String!
  }

  type Person {
    name: String!
    phone: String
    address: Address!
    id: ID!
  }

  enum YesNo {
    YES
    NO
  }

  type Query {
    personCount: Int!
    allPersons(phone: YesNo): [Person!]!
    findPerson(name: String!): Person
  }

  type Mutation {
    addPerson(
      name: String!
      phone: String
      street: String!
      city: String!
    ): Person
    editNumber(name: String!, phone: String!): Person
  }
`

module.exports = typeDefs
```

Next, we'll move the code responsible for the resolvers into its own module, *resolvers.js*:

```javascript
const { GraphQLError } = require('graphql')
const { v1: uuid } = require('uuid')

let persons = [
  {
    name: 'Arto Hellas',
    phone: '040-123543',
    street: 'Tapiolankatu 5 A',
    city: 'Espoo',
    id: '3d594650-3436-11e9-bc57-8b80ba54c431',
  },
  {
    name: 'Matti Luukkainen',
    phone: '040-432342',
    street: 'Malminkaari 10 A',
    city: 'Helsinki',
    id: '3d599470-3436-11e9-bc57-8b80ba54c431',
  },
  {
    name: 'Venla Ruuska',
    street: 'Nallemäentie 22 C',
    city: 'Helsinki',
    id: '3d599471-3436-11e9-bc57-8b80ba54c431',
  },
]

const resolvers = {
  Query: {
    personCount: () => persons.length,
    allPersons: (root, args) => {
      if (!args.phone) {
        return persons
      }
      const byPhone = (person) =>
        args.phone === 'YES' ? person.phone : !person.phone
      return persons.filter(byPhone)
    },
    findPerson: (root, args) => persons.find((p) => p.name === args.name),
  },
  Person: {
    address: ({ street, city }) => {
      return {
        street,
        city,
      }
    },
  },
  Mutation: {
    addPerson: (root, args) => {
      if (persons.find((p) => p.name === args.name)) {
        throw new GraphQLError(`Name must be unique: ${args.name}`, {
          extensions: {
            code: 'BAD_USER_INPUT',
            invalidArgs: args.name,
          },
        })
      }

      const person = { ...args, id: uuid() }
      persons = persons.concat(person)
      return person
    },
    editNumber: (root, args) => {
      const person = persons.find((p) => p.name === args.name)
      if (!person) {
        return null
      }

      const updatedPerson = { ...person, phone: args.phone }
      persons = persons.map((p) => (p.name === args.name ? updatedPerson : p))
      return updatedPerson
    },
  },
}

module.exports = resolvers
```

For simplicity, the *persons* array that holds the people's data is now placed in the same file as the resolvers. The array will soon be removed when we switch to using a database for storing data.

Finally, we'll also move the code responsible for starting the Apollo server into its own file, *server.js*:

```javascript
const { ApolloServer } = require('@apollo/server')
const { startStandaloneServer } = require('@apollo/server/standalone')

const resolvers = require('./resolvers')
const typeDefs = require('./schema')

const startServer = (port) => {
  const server = new ApolloServer({
    typeDefs,
    resolvers,
  })

  startStandaloneServer(server, {
    listen: { port },
  }).then(({ url }) => {
    console.log(`Server ready at ${url}`)
  })
}

module.exports = startServer
```

Starting the Apollo server is now handled inside the *startServer* function we defined ourselves. This lets us export the function and start the server from outside the module, from the *index.js* file. The function takes as a parameter the port that Apollo Server will listen on.

Let's install the *dotenv* library so that we can define environment variables in a *.env* file:

```
npm install dotenv
```

The contents of the *index.js* file are now as follows:

```javascript
require('dotenv').config()

const startServer = require('./server')

const PORT = process.env.PORT || 4000

startServer(PORT)
```

Environment variables are first read from the *.env* file using the *dotenv* library. The port to use is now read from an environment variable, if one is set. If the *PORT* environment variable is not found, the default port 4000 is used—which is also the port the frontend currently expects the server to be running on. Finally, Apollo Server is started by calling the function startServer.

For now, the contents of *index.js* are just a stub, but as the application grows it will include more. For example, when we soon switch to using a database for storing data, the database connection must be created before starting the server.

The responsibilities of the application are now clearly separated:

- *index.js* acts as the main program, whose only responsibility is the startup logic. It ensures that different parts of the application are started in the correct order.
- The GraphQL schema is defined in the *schema.js* module.
- The resolvers are defined in the *resolvers.js* module.
- The code responsible for starting the Apollo Server is in the *server.js* module.

## Connecting to a database

Let's connect the application to a MongoDB database. We'll use [Mongoose](https://mongoosejs.com/) to interact with the database.

Let's install Mongoose:

```
npm install mongoose
```

Let's define the Mongoose schema for a person in the file *models/person.js*:

```javascript
const mongoose = require('mongoose')

const schema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    minlength: 5
  },
  phone: {
    type: String,
    minlength: 5
  },
  street: {
    type: String,
    required: true,
    minlength: 5
  },
  city: {
    type: String,
    required: true,
    minlength: 3
  },
})

module.exports = mongoose.model('Person', schema)
```

We also included a few validations. `required: true`, which makes sure that a value exists, is actually redundant: we already ensure that the fields exist with GraphQL. However, it is good to also keep validation in the database.

Let's create a separate module *db.js* for the code that establishes the database connection:

```javascript
const mongoose = require('mongoose')

const connectToDatabase = async (uri) => {
  console.log('connecting to database URI:', uri)

  try {
    await mongoose.connect(uri)
    console.log('connected to MongoDB')
  } catch (error) {
    console.log('error connection to MongoDB:', error.message)
    process.exit(1)
  }
}

module.exports = connectToDatabase
```

The module defines the function `connectToDatabase`, which receives the database URI as a parameter and takes care of connecting to the database.

Let's use the module in the file *index.js*:

```javascript
require('dotenv').config()
const connectToDatabase = require('./db')
const startServer = require('./server')

const MONGO_URI = process.env.MONGO_URI

connectToDatabase(MONGO_URI)

const PORT = process.env.PORT || 4000

startServer(PORT)
```

The application now establishes a connection to the database before starting the server.

## Resolvers and database

Let's change the resolvers so that they use the database instead of the in-memory array. The file *resolvers.js* now looks like this:

```javascript
const { GraphQLError } = require('graphql')
const Person = require('./models/person')

const resolvers = {
  Query: {
    personCount: async () => Person.collection.countDocuments(),
    allPersons: async (root, args) => {
      // filters missing
      return Person.find({})
    },
    findPerson: async (root, args) => Person.findOne({ name: args.name }),
  },
  Person: {
    address: ({ street, city }) => {
      return {
        street,
        city,
      }
    },
  },
  Mutation: {
    addPerson: async (root, args) => {
      const nameExists = await Person.exists({ name: args.name })

      if (nameExists) {
        throw new GraphQLError(`Name must be unique: ${args.name}`, {
          extensions: {
            code: 'BAD_USER_INPUT',
            invalidArgs: args.name,
          },
        })
      }

      const person = new Person({ ...args })
      return person.save()
    },
    editNumber: async (root, args) => {
      const person = await Person.findOne({ name: args.name })

      if (!person) {
        return null
      }

      person.phone = args.phone
      return person.save()
    },
  },
}

module.exports = resolvers
```

The changes are pretty straightforward. However, there are a few noteworthy things. As we remember, in Mongo, the identifying field of an object is called *_id* and we previously had to parse the name of the field to *id* ourselves. Now GraphQL can do this automatically.

Another noteworthy thing is that the resolver functions now return a *promise*, when they previously returned normal objects. When a resolver returns a promise, Apollo server [sends back](https://www.apollographql.com/docs/apollo-server/data/resolvers#return-values) the value which the promise resolves to.

For example, if the following resolver function is executed,

```javascript
allPersons: async (root, args) => {
  return Person.find({})
},
```

Apollo server waits for the promise to resolve, and returns the result. So Apollo works roughly like this:

```javascript
allPersons: async (root, args) => {
  const result = await Person.find({})
  return result
}
```

Let's complete the `allPersons` resolver so it takes the optional parameter `phone` into account:

```javascript
Query: {
  // ..
  allPersons: async (root, args) => {
    if (!args.phone) {
      return Person.find({})
    }

    return Person.find({ phone: { $exists: args.phone === 'YES' } })
  },
},
```

So if the query has not been given a parameter `phone`, all persons are returned. If the parameter has the value *YES*, the result of the query

```javascript
Person.find({ phone: { $exists: true }})
```

is returned, so the objects in which the field `phone` has a value. If the parameter has the value *NO*, the query returns the objects in which the `phone` field has no value:

```javascript
Person.find({ phone: { $exists: false }})
```

## User administration

Let's expand the application to support user administration. The idea is that each user has their own *friends* list, to which they can add people.

Let's define the Mongoose schema for a user in the file *models/user.js*:

```javascript
const mongoose = require('mongoose')

const schema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    minlength: 3
  },
  friends: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Person'
    }
  ],
})

module.exports = mongoose.model('User', schema)
```

Every user is connected to a bunch of other persons in the system through the `friends` field. The idea is that when a user, e.g. *mluukkai*, adds a person, e.g. *Arto Hellas*, to the list, the person is added to their `friends` list. This way, logged-in users can have their own personalized view in the application.

Logging in and identifying the user are handled the same way we used in [part 4](https://fullstackopen.com/en/part4/token_authentication) when we used REST, by using tokens.

Let's extend the GraphQL schema like so:

```graphql
type User {
  username: String!
  friends: [Person!]!
  id: ID!
}

type Token {
  value: String!
}

type Query {
  // ..
  me: User
}

type Mutation {
  // ...
  createUser(username: String!): User
  login(username: String!, password: String!): Token
}
```

The query `me` returns the currently logged-in user. New users are created with the `createUser` mutation, and logging in happens with the `login` mutation.

Let's install the jsonwebtoken library:

```
npm install jsonwebtoken
```

The resolvers of the new mutations are as follows:

```javascript
const jwt = require('jsonwebtoken')
const User = require('./models/user')

Mutation: {
  // ..
  createUser: async (root, args) => {
    const user = new User({ username: args.username })

    return user.save()
      .catch(error => {
        throw new GraphQLError(`Creating the user failed: ${error.message}`, {
          extensions: {
            code: 'BAD_USER_INPUT',
            invalidArgs: args.username,
            error
          }
        })
      })
  },
  login: async (root, args) => {
    const user = await User.findOne({ username: args.username })

    if ( !user || args.password !== 'secret' ) {
      throw new GraphQLError('wrong credentials', {
        extensions: {
          code: 'BAD_USER_INPUT'
        }
      })
    }

    const userForToken = {
      username: user.username,
      id: user._id,
    }

    return { value: jwt.sign(userForToken, process.env.JWT_SECRET) }
  },
},
```

The new user mutation is straightforward. The login mutation checks if the username/password pair is valid. And if it is indeed valid, it returns a jwt token familiar from [part 4](https://fullstackopen.com/en/part4/token_authentication). Note that the `JWT_SECRET` must be defined in the *.env* file.

User creation is done now as follows:

```graphql
mutation {
  createUser (
    username: "mluukkai"
  ) {
    username
    id
  }
}
```

The mutation for logging in looks like this:

```graphql
mutation {
  login (
    username: "mluukkai"
    password: "secret"
  ) {
    value
  }
}
```

Just like in the previous case with REST, the idea now is that a logged-in user adds a token they receive upon login to all of their requests. And just like with REST, the token is added to GraphQL queries using the *Authorization* header.

In the Apollo Explorer, the header is added to a query like so:

![Apollo Explorer highlighting headers with authorization and bearer token - Shows the Apollo Explorer interface with the HEADERS panel open, displaying JSON with an "Authorization" key set to "Bearer <token>". The headers section is highlighted to show where the JWT bearer token should be added for authenticated requests.](https://courses.mooc.fi/api/v0/files/course/d96d7ec8-4c2b-43fc-bf46-94ebb7fa4fe8/images/mD67dBQkw8zAialvOqqVhiXgbeFw5w.png)

On the backend, the most convenient way to pass the token that arrives with the request to the resolvers is to use Apollo Server's [context](https://www.apollographql.com/docs/apollo-server/data/context/). With the context, we can perform things that are common to all queries and mutations, for example [identifying the user](https://www.apollographql.com/blog/authorization-in-graphql/) associated with the request.

Let's change the backend startup so that the object passed as the second parameter to the [startStandaloneServer](https://www.apollographql.com/docs/apollo-server/api/standalone/) function includes a [context](https://www.apollographql.com/docs/apollo-server/data/context/) field, and let's create a helper function `getUserFromAuthHeader` to verify the validity of the token and to find the user from the database:

```javascript
const { ApolloServer } = require('@apollo/server')
const { startStandaloneServer } = require('@apollo/server/standalone')
const jwt = require('jsonwebtoken')

const resolvers = require('./resolvers')
const typeDefs = require('./schema')
const User = require('./models/user')

const getUserFromAuthHeader = async (auth) => {
  if (!auth || !auth.startsWith('Bearer ')) {
    return null
  }

  const decodedToken = jwt.verify(auth.substring(7), process.env.JWT_SECRET)
  return User.findById(decodedToken.id).populate('friends')
}

const startServer = (port) => {
  const server = new ApolloServer({
    typeDefs,
    resolvers,
  })

  startStandaloneServer(server, {
    listen: { port },
    context: async ({ req }) => {
      const auth = req.headers.authorization
      const currentUser = await getUserFromAuthHeader(auth)
      return { currentUser }
    },
  }).then(({ url }) => {
    console.log(`Server ready at ${url}`)
  })
}

module.exports = startServer
```

So the code we defined first extracts the token contained in the request's `Authorization` header. The helper function `getUserFromAuthHeader` decodes the token and looks up the corresponding user from the database. If the token is not valid or the user cannot be found, the function returns `null`.

Finally, the context field `currentUser` is set to the user object corresponding to the requester, or to `null` if no user was found:

```javascript
context: async ({ req }) => {
  const auth = req.headers.authorization
  const currentUser = await getUserFromAuthHeader(auth)
  return { currentUser }
},
```

The context value is passed to resolvers as the `third parameter`. The resolver for the `me` query is very simple: it only returns the currently logged-in user, which it gets from the resolver parameter `context`, from the field `currentUser`:

```javascript
Query: {
  // ...
  me: (root, args, context) => {
    return context.currentUser
  }
},
```

If the header contains a valid token, the query returns the details of the user identified by the token.

![Apollo Studio showing query response object - Shows Apollo Studio (Explorer) with a GraphQL query for "me" and its response. The response panel displays a JSON object containing the logged-in user's data including username, friends list, and id, demonstrating that the context-based authentication is working correctly.](https://courses.mooc.fi/api/v0/files/course/d96d7ec8-4c2b-43fc-bf46-94ebb7fa4fe8/images/wqi8pJhWHargSYChK04eREhRsC9ZNM.png)

## Friends list

Let's complete the application's backend so that adding and editing persons requires logging in, and added persons are automatically added to the friends list of the user.

Let's first remove all persons not in anyone's friends list from the database.

`addPerson` mutation changes like so:

```javascript
Mutation: {
  addPerson: async (root, args, context) => {
    const currentUser = context.currentUser

    if (!currentUser) {
      throw new GraphQLError('not authenticated', {
        extensions: {
          code: 'UNAUTHENTICATED',
        }
      })
    }

    const nameExists = await Person.exists({ name: args.name })

    if (nameExists) {
      throw new GraphQLError(`Name must be unique: ${args.name}`, {
        extensions: {
          code: 'BAD_USER_INPUT',
          invalidArgs: args.name,
        },
      })
    }

    const person = new Person({ ...args })

    try {
      await person.save()
      currentUser.friends = currentUser.friends.concat(person)
      await currentUser.save()
    } catch (error) {
      throw new GraphQLError(`Saving person failed: ${error.message}`, {
        extensions: {
          code: 'BAD_USER_INPUT',
          invalidArgs: args.name,
          error
        }
      })
    }

    return person
  },
  //...
}
```

If a logged-in user cannot be found from the context, an `GraphQLError` with a proper message is thrown. Creating new persons is now done with `async/await` syntax, because if the operation is successful, the created person is added to the friends list of the user.

Let's also add the ability to add a person to your own friends list. The mutation schema is as follows:

```graphql
type Mutation {
  // ...
  addAsFriend(name: String!): User
}
```

And the mutation's resolver:

```javascript
  addAsFriend: async (root, args, { currentUser }) => {
    if (!currentUser) {
      throw new GraphQLError('not authenticated', {
        extensions: { code: 'UNAUTHENTICATED' },
      })
    }

    const nonFriendAlready = (person) =>
      !currentUser.friends
        .map((f) => f._id.toString())
        .includes(person._id.toString())

    const person = await Person.findOne({ name: args.name })

    if (!person) {
      throw new GraphQLError("The name didn't found", {
        extensions: {
          code: 'BAD_USER_INPUT',
          invalidArgs: args.name,
        },
      })
    }

    if (nonFriendAlready(person)) {
      currentUser.friends = currentUser.friends.concat(person)
    }

    await currentUser.save()

    return currentUser
  },
```

Note how the resolver *destructures* the logged-in user from the context. So instead of saving `currentUser` to a separate variable in a function

```javascript
addAsFriend: async (root, args, context) => {
  const currentUser = context.currentUser
```

it is received straight in the parameter definition of the function:

```javascript
addAsFriend: async (root, args, { currentUser }) => {
```

The following query now returns the user's friends list:

```graphql
query {
  me {
    username
    friends{
      name
      phone
    }
  }
}
```

The code of the backend can be found on [Github](https://github.com/fullstack-hy2020/graphql-phonebook-backend/tree/part8-5) branch *part8-5*.

---

## Invalid input

Please check your input and try again.

<details>
<summary>Show source</summary>

- Status: 422
- Request ID: b79f67f5-9473-4896-b699-7e72dab5aaed
- Type: validation_error
- Message key: validation_error
- Method: GET
- URL: https://courses.mooc.fi/api/v0/course-material/exercises/be23a471-1184-4015-ab92-e49a57224e3e
- User must be enrolled to the course
- ```json
  {
    "type": "validation_error",
    "messageKey": "validation_error",
    "code": null,
    "message": "User must be enrolled to the course",
    "status": 422,
    "issues": [],
    "metadata": null,
    "extra": null,
    "body": {
      "type": "validation_error",
      "message_key": "validation_error",
      "message": "User must be enrolled to the course"
    },
    "rawText": null
  }
  ```

</details>

## Invalid input

Please check your input and try again.

<details>
<summary>Show source</summary>

- Status: 422
- Request ID: b0ed1d9e-4095-4c42-b752-8354a36993b4
- Type: validation_error
- Message key: validation_error
- Method: GET
- URL: https://courses.mooc.fi/api/v0/course-material/exercises/54a91234-4ab7-45f4-9dee-3843d5fe63bc
- User must be enrolled to the course
- ```json
  {
    "type": "validation_error",
    "messageKey": "validation_error",
    "code": null,
    "message": "User must be enrolled to the course",
    "status": 422,
    "issues": [],
    "metadata": null,
    "extra": null,
    "body": {
      "type": "validation_error",
      "message_key": "validation_error",
      "message": "User must be enrolled to the course"
    },
    "rawText": null
  }
  ```

</details>

## Invalid input

Please check your input and try again.

<details>
<summary>Show source</summary>

- Status: 422
- Request ID: 6fe91b13-7d31-4ad0-9c9b-f1963afc7dae
- Type: validation_error
- Message key: validation_error
- Method: GET
- URL: https://courses.mooc.fi/api/v0/course-material/exercises/35bd63d2-d047-447d-a3e7-a3297242f1ca
- User must be enrolled to the course
- ```json
  {
    "type": "validation_error",
    "messageKey": "validation_error",
    "code": null,
    "message": "User must be enrolled to the course",
    "status": 422,
    "issues": [],
    "metadata": null,
    "extra": null,
    "body": {
      "type": "validation_error",
      "message_key": "validation_error",
      "message": "User must be enrolled to the course"
    },
    "rawText": null
  }
  ```

</details>

## Invalid input

Please check your input and try again.

<details>
<summary>Show source</summary>

- Status: 422
- Request ID: 28de9074-04cd-45ef-9fa5-39b94059520f
- Type: validation_error
- Message key: validation_error
- Method: GET
- URL: https://courses.mooc.fi/api/v0/course-material/exercises/b3d08725-5cfc-4237-b975-1c8517a60e92
- User must be enrolled to the course
- ```json
  {
    "type": "validation_error",
    "messageKey": "validation_error",
    "code": null,
    "message": "User must be enrolled to the course",
    "status": 422,
    "issues": [],
    "metadata": null,
    "extra": null,
    "body": {
      "type": "validation_error",
      "message_key": "validation_error",
      "message": "User must be enrolled to the course"
    },
    "rawText": null
  }
  ```

</details>

## Invalid input

Please check your input and try again.

<details>
<summary>Show source</summary>

- Status: 422
- Request ID: 90c47fc8-6914-4147-994c-c971a75aef57
- Type: validation_error
- Message key: validation_error
- Method: GET
- URL: https://courses.mooc.fi/api/v0/course-material/exercises/2812cdb5-321b-4b12-8285-4c2a29a265fe
- User must be enrolled to the course
- ```json
  {
    "type": "validation_error",
    "messageKey": "validation_error",
    "code": null,
    "message": "User must be enrolled to the course",
    "status": 422,
    "issues": [],
    "metadata": null,
    "extra": null,
    "body": {
      "type": "validation_error",
      "message_key": "validation_error",
      "message": "User must be enrolled to the course"
    },
    "rawText": null
  }
  ```

</details>

> Please log in to lock a chapter.
