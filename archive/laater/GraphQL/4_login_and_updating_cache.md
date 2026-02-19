# Chapter 5: Login and updating the cache


The frontend of our application shows the phone directory just fine with the updated server. However, if we want to add new persons, we have to add login functionality to the frontend.

## User login

Let’s first define the mutation for logging in in the file *src/queries.js*:
```autoit
export const LOGIN = gql`
  mutation login($username: String!, $password: String!) {
    login(username: $username, password: $password)  {
      value
    }
  }
`
```

Let’s define the `LoginForm` component responsible for logging in in the file *src/components/LoginForm.jsx*. It works in much the same way as the earlier components that handle mutations. The interesting lines are highlighted in the code:
```javascript
import { useState } from 'react'
import { useMutation } from '@apollo/client/react'
import { LOGIN } from '../queries'

const LoginForm = ({ setError, setToken }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const [ login ] = useMutation(LOGIN, {
    onCompleted: (data) => {
      const token = data.login.value
      setToken(token)
      localStorage.setItem('phonebook-user-token', token)
    },
    onError: (error) => {
      setError(error.message)
    }
  })

  const submit = (event) => {
    event.preventDefault()
    login({ variables: { username, password } })
  }

  return (
    <div>
      <form onSubmit={submit}>
        <div>
          username <input
            value={username}
            onChange={({ target }) => setUsername(target.value)}
          />
        </div>
        <div>
          password <input
            type='password'
            value={password}
            onChange={({ target }) => setPassword(target.value)}
          />
        </div>
        <button type='submit'>login</button>
      </form>
    </div>
  )
}

export default LoginForm
```

The component receives the functions `setError` and `setToken` as props, which can be used to change the application state. Defining state management is left to the `App` component.

For the `useMutation` function that performs the login, an `onCompleted` callback function is defined. It is called when the mutation has been successfully executed. In the callback, the token value is read from the response data and then stored in the application state and in the browser’s localStorage.

Let’s now use the *LoginForm* component in the *App.jsx* file. We add a `token` variable to the application state to store the token once the user has logged in. If `token` is not defined, we render only the login form:
```javascript
import LoginForm from './components/LoginForm'
// ...

const App = () => {
  const [token, setToken] = useState(localStorage.getItem('phonebook-user-token'))
  const [errorMessage, setErrorMessage] = useState(null)
  const result = useQuery(ALL_PERSONS)

  if (result.loading) {
    return <div>loading...</div>
  }

  const notify = (message) => {
    setErrorMessage(message)
    setTimeout(() => {
      setErrorMessage(null)
    }, 10000)
  }

  if (!token) {
    return (
      <div>
        <Notify errorMessage={errorMessage} />
        <h2>Login</h2>
        <LoginForm
          setToken={setToken}
          setError={notify}
        />
      </div>
    )
  }

  return (
    // ...
  )
}
```

The token is now initialized from a token value that may be found in localStorage:
```stylus
const [token, setToken] = useState(localStorage.getItem('phonebook-user-token'))
```

This way, the token is also restored when the page is reloaded, and the user stays logged in. If localStorage does not contain a value for the key *phonebook-user-token*, the token value will be `null`.

We also add a button that allows a logged-in user to log out. In the button’s click handler, we set `token` to `null`, remove the token from localStorage, and reset the Apollo Client cache:
```javascript
import { useApolloClient, useQuery } from '@apollo/client/react'
//...

const App = () => {
  const [token, setToken] = useState(null)
  const [errorMessage, setErrorMessage] = useState(null)
  const result = useQuery(ALL_PERSONS)
  const client = useApolloClient()
  
  if (result.loading)  {
    return <div>loading...</div>
  }

  const onLogout = () => {
    setToken(null)
    localStorage.clear()
    client.resetStore()
  }

  // ...

  return (
    <>
      <Notify errorMessage={errorMessage} />
      <button onClick={onLogout}>logout</button>
      <Persons persons={result.data.allPersons} />
      <PersonForm setError={notify} />
      <PhoneForm setError={notify} />
    </>
  )
}
```

Resetting the cache is done using the Apollo `client` object’s [resetStore (opens in a new tab)](https://www.apollographql.com/docs/react/api/core/ApolloClient#resetstore) method, and the client itself can be accessed with the [useApolloClient (opens in a new tab)](https://www.apollographql.com/docs/react/api/react/useApolloClient) hook. Clearing the cache is [important (opens in a new tab)](https://www.apollographql.com/docs/react/networking/authentication/#reset-store-on-logout), because some queries may have fetched data into the cache that only an authenticated user is allowed to access.

## Adding a token to a header

After the backend changes, creating new persons requires that a valid user token is sent with the request. This requires changes to the Apollo Client configuration in the *main.jsx* file:
```javascript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

import { ApolloClient, HttpLink, InMemoryCache } from '@apollo/client'
import { ApolloProvider } from '@apollo/client/react'
import { SetContextLink } from '@apollo/client/link/context'

const authLink  = new SetContextLink(({ headers }) => {
  const token = localStorage.getItem('phonebook-user-token')
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : null,
    }
  }
})

const httpLink = new HttpLink({ uri: 'http://localhost:4000' })

const client = new ApolloClient({
  cache: new InMemoryCache(),
  link: authLink.concat(httpLink)
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ApolloProvider client={client}>
      <App />
    </ApolloProvider>
  </StrictMode>,
)
```

As before, the server URL is wrapped using the [HttpLink (opens in a new tab)](https://www.apollographql.com/docs/react/api/link/apollo-link-http) constructor to create a suitable `httpLink` object. This time, however, it is modified using the [context (opens in a new tab)](https://www.apollographql.com/docs/react/api/link/apollo-link-context/#overview) defined by the `authLink` object so that, for each request, the *authorization* header is [set (opens in a new tab)](https://www.apollographql.com/docs/react/networking/authentication/#header) to the token that may be stored in localStorage.

Creating new persons and changing numbers works again.

## Fixing validations

In the application, it should be possible to add a person without a phone number. However, if we now try to add a person without a phone number, it doesn’t work:

![browser showing person validation failed](https://courses.mooc.fi/api/v0/files/course/d96d7ec8-4c2b-43fc-bf46-94ebb7fa4fe8/images/iFWQLhDJAHTgSxFffVIolLbyo0Bvn9.png)

Validation fails, because frontend sends an empty string as the value of `phone`.

Let's change the function creating new persons so that it sets `phone` to `undefined` if user has not given a value:
```javascript
const PersonForm = ({ setError }) => {
  // ...
  const submit = async (event) => {
    event.preventDefault()

    createPerson({
      variables: {
        name,
        street,
        city,
        phone: phone.length > 0 ? phone : undefined,
      },
    })

    setName('')
    setPhone('')
    setStreet('')
    setCity('')
  }

  // ...
}
```

From the perspective of the backend and the database, the *phone* attribute now has no value if the user leaves the field empty. Adding a person without a phone number works again.

There is also an issue with the functionality for changing a phone number. The database validations require that the phone number must be at least 5 characters long, but if we try to update an existing person’s phone number to one that is too short, nothing seems to happen. The person’s phone number is not updated, but on the other hand no error message is shown either.

From the console’s *Network* tab we can see that the request is answered with an error message:

![The console’s Network tab shows the error message returned in the response](https://courses.mooc.fi/api/v0/files/course/d96d7ec8-4c2b-43fc-bf46-94ebb7fa4fe8/images/tI5HOb8i5Pj92hg9dyg4268TvqADcU.png)

Let’s modify the application so that validation errors are also shown when changing a phone number:
```javascript
const PhoneForm = ({ setError }) => {
  // ...

  const submit = async (event) => {
    event.preventDefault()

    try {
      await changeNumber({ variables: { name, phone } })
    } catch (error) {
      setError(error.message)
    }

    setName('')
    setPhone('')
  }

  // ...
}
```

The request that updates the number, `changeNumber`, is now executed inside a *try* block. If the database validations fail, execution ends up in the *catch* block, where an appropriate error message is set in the application using the `setError` function:

![The application shows an error message if the phone number is shorter than 5 characters](https://courses.mooc.fi/api/v0/files/course/d96d7ec8-4c2b-43fc-bf46-94ebb7fa4fe8/images/mYTHYbVMHOJey2HrC7QdjMe6ZoCQip.png)

## Updating cache, revisited

We have to [update (opens in a new tab)](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-graphql/chapter-3#updating-the-cache) the cache of the Apollo client on creating new persons. We can update it using the mutation's `refetchQueries` option to define that the `ALL_PERSONS` query is done again.
```javascript
const PersonForm = ({ setError }) => {
  // ...

  const [createPerson] = useMutation(CREATE_PERSON, {
    onError: (error) => setError(error.message),
    refetchQueries: [{ query: ALL_PERSONS }],
  })

// ...
}
```

This approach is pretty good, the drawback being that the query is always rerun with any updates.

It is possible to optimize the solution by updating the cache manually. This is done by defining an appropriate [update (opens in a new tab)](https://www.apollographql.com/docs/react/data/mutations/#the-update-function) callback for the mutation instead of using the `refetchQueries` attribute. Apollo executes this callback after the mutation completes:
```moonscript
const PersonForm = ({ setError }) => {
  // ...

  const [createPerson] = useMutation(CREATE_PERSON, {
    onError: (error) => setError(error.message),
    update: (cache, response) => {
      cache.updateQuery({ query: ALL_PERSONS }, ({ allPersons }) => {
        return {
          allPersons: allPersons.concat(response.data.addPerson),
        }
      })
    },
  })
 
  // ..
}  
```

The callback function is given a reference to the cache and the data returned by the mutation as parameters. For example, in our case, this would be the created person.

Using the function [updateQuery (opens in a new tab)](https://www.apollographql.com/docs/react/caching/cache-interaction/#using-updatequery-and-updatefragment) the code updates the query ALLPERSONS in the cache by adding the new person to the cached data.

In some situations, the only sensible way to keep the cache up to date is using the `update` callback.

When necessary, it is possible to disable cache for the whole application or [single queries (opens in a new tab)](https://www.apollographql.com/docs/react/api/react/hooks/#options) by setting the field managing the use of cache, [fetchPolicy (opens in a new tab)](https://www.apollographql.com/docs/react/data/queries#setting-a-fetch-policy) as `no-cache`.

Be diligent with the cache. Old data in the cache can cause hard-to-find bugs. As we know, keeping the cache up to date is very challenging. According to a coder proverb:

> There are only two hard things in Computer Science: cache invalidation and naming things. Read more here (opens in a new tab).

The current code of the application can be found on [Github (opens in a new tab)](https://github.com/fullstack-hy2020/graphql-phonebook-frontend/tree/part8-5), branch *part8-5*.