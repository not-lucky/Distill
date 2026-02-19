| Fullstack | Part 2 | Adding styles to React app |
| :--- | :--- | :--- |
| **{ } => fs** | **About course** **Course contents** **FAQ** **Partners** **Challenge** | 🔍 ☀ English ▼ |

***

**Fullstack** > **Part 2** > **Adding styles to React app**

*   a Rendering a collection, modules
*   b Forms
*   c Getting data from server
*   d Altering data in server
*   **e Adding styles to React app**
    *   Improved error message
    *   Inline styles
    *   Exercises 2.16.-2.17.
    *   Couple of important remarks
    *   Exercises 2.18.-2.20.

***

# ⓔ Adding styles to React app

The appearance of our current Notes application is quite modest. In [exercise 0.2](https://fullstackopen.com/en/part0/fundamentals_of_web_apps#exercises-0-1-0-6), the assignment was to go through Mozilla's CSS tutorial.

Let's take a look at how we can add styles to a React application. There are several different ways of doing this and we will take a look at the other methods later on. First, we will add CSS to our application the old-school way; in a single file without using a CSS preprocessor (although this is not entirely true as we will learn later on).

Let's add a new *index.css* file under the src directory and then add it to the application by importing it in the *main.jsx* file.

```javascript
import './index.css'
```

Let's add the following CSS rule to the index.css file:

```css
h1 {
  color: green;
}
```

CSS rules comprise of *selectors* and *declarations*. The selector defines which elements the rule should be applied to. The selector above is `h1`, which will match all of the `h1` header tags in the application.

The declaration sets the `color` property to the value `green`.

One CSS rule can contain an arbitrary number of properties. Let's modify the previous rule to make the text cursive, by defining the font style as italic:

```css
h1 {
  color: green;
  font-style: italic;
}
```

There are many ways of matching elements by using different types of CSS selectors.

If we wanted to target, let's say, each one of the notes with our styles, we could use the selector `li`, as all of the notes are wrapped inside `li` tags:

```jsx
const Note = ({ note, toggleImportance }) => {
  const label = note.important
    ? 'make not important'
    : 'make important'

  return (
    <li>
      {note.content}
      <button onClick={toggleImportance}>{label}</button>
    </li>
  )
}
```

Let's add the following rule to our style sheet (since my knowledge of elegant web design is close to zero, the styles don't make much sense):

```css
li {
  color: grey;
  padding-top: 5px;
  font-size: 15px;
}
```

Using element types for defining CSS rules is slightly problematic. If our application contained other `li` tags, the same style rule would also be applied to them.

If we want to apply our style specifically to notes, then it is better to use [class selectors](https://developer.mozilla.org/en-US/docs/Web/CSS/Class_selectors).

In regular HTML, classes are defined as the value of the *class* attribute:

```html
<li class="some-text">...</li>
```

In React we have to use the *className* attribute instead of the class attribute. With this in mind, let's make the following changes to our `Note` component:

```jsx
const Note = ({ note, toggleImportance }) => {
  const label = note.important
    ? 'make not important'
    : 'make important'

  return (
    <li className="note">
      {note.content}
      <button onClick={toggleImportance}>{label}</button>
    </li>
  )
}
```

Class selectors are defined with the `.classname` syntax:

```css
.note {
  color: grey;
  padding-top: 5px;
  font-size: 15px;
}
```

If you now add other `li` elements to the application, they will not be affected by the style rule above.

### Improved error message

We previously implemented the error message that was displayed when the user tried to toggle the importance of a deleted note with the `alert` method. Let's implement the error message as its own React component in the file *src/components/Notification.jsx*.

The component is quite simple:

```jsx
const Notification = ({ message }) => {
  if (message === null) {
    return null
  }

  return (
    <div className="error">
      {message}
    </div>
  )
}

export default Notification
```

If the value of the `message` prop is `null`, then nothing is rendered to the screen, and in other cases, the message gets rendered inside of a div element.

Let's add a new piece of state called *errorMessage* to the *App* component. Let's initialize it with some error message so that we can immediately test our component:

```jsx
import { useState, useEffect } from 'react'
import Note from './components/Note'
import Notification from './components/Notification'
import noteService from './services/notes'

const App = () => {
  const [notes, setNotes] = useState([])
  const [newNote, setNewNote] = useState('')
  const [showAll, setShowAll] = useState(true)
  const [errorMessage, setErrorMessage] = useState('some error happened...')

  return (
    <div>
      <h1>Notes</h1>
      <Notification message={errorMessage} />
      <div>
        <button onClick={() => setShowAll(!showAll)}>
          show {showAll ? 'important' : 'all' }
        </button>
      </div>
      {/* ... */}
    </div>
  )
}
```

Then let's add a style rule that suits an error message:

```css
.error {
  color: red;
  background: lightgrey;
  font-size: 20px;
  border-style: solid;
  border-radius: 5px;
  padding: 10px;
  margin-bottom: 10px;
}
```

Now we are ready to add the logic for displaying the error message. Let's change the `toggleImportanceOf` function in the following way:

```jsx
  const toggleImportanceOf = id => {
    const note = notes.find(n => n.id === id)
    const changedNote = { ...note, important: !note.important }

    noteService
      .update(id, changedNote).then(returnedNote => {
        setNotes(notes.map(note => note.id !== id ? note : returnedNote))
      })
      .catch(error => {
        setErrorMessage(
          `Note '${note.content}' was already removed from server`
        )
        setTimeout(() => {
          setErrorMessage(null)
        }, 5000)
        setNotes(notes.filter(n => n.id !== id))
      })
  }
```

When the error occurs we add a descriptive error message to the `errorMessage` state. At the same time, we start a timer, that will set the `errorMessage` state to `null` after five seconds.

The result looks like this:

![Browser showing a red error notification: Note 'This note is not saved to server' was already removed from server](https://fullstackopen.com/static/0d27863158428574161988950d481546/5a190/19e.png)

The code for the current state of our application can be found in the [part2-7](https://github.com/fullstack-hy2020/part2-notes-frontend/tree/part2-7) branch on GitHub.

### Inline styles

React also makes it possible to write styles directly in the code as so-called *inline styles*.

The idea behind defining inline styles is extremely simple. Any React component or element can be provided with a set of CSS properties as a JavaScript object through the *style* attribute.

CSS rules are defined slightly differently in JavaScript than in normal CSS files. Let's say that we wanted to give some element the color green and italic font. In CSS, it would look like this:

```css
{
  color: green;
  font-style: italic;
}
```

But as a React inline-style object it would look like this:

```javascript
{
  color: 'green',
  fontStyle: 'italic'
}
```

Every CSS property is defined as a separate property of the JavaScript object. Numeric values for pixels can be simply defined as integers. One of the major differences compared to regular CSS, is that hyphenated (kebab-case) CSS properties are written in camelCase.

Let's add a *Footer* component, *Footer*, to our application and define inline styles for it. The component is defined in the file *src/components/Footer.jsx* and used in the file *App.jsx* as follows:

```jsx
const Footer = () => {
  const footerStyle = {
    color: 'green',
    fontStyle: 'italic',
    fontSize: 16
  }
  return (
    <div style={footerStyle}>
      <br />
      <em>Note app, Department of Computer Science, University of Helsinki 2023</em>
    </div>
  )
}

export default Footer
```

```jsx
import { useState, useEffect } from 'react'
import Note from './components/Note'
import Notification from './components/Notification'
import Footer from './components/Footer'
import noteService from './services/notes'

const App = () => {
  // ...
  return (
    <div>
      <h1>Notes</h1>
      <Notification message={errorMessage} />
      {/* ... */}
      <Footer />
    </div>
  )
}
```

Inline styles come with certain limitations. For instance, so-called [pseudo-classes](https://developer.mozilla.org/en-US/docs/Web/CSS/Pseudo-classes) can't be used straightforwardly.

Inline styles and some of the other ways of adding styles to React components go completely against the grain of old conventions. Traditionally, it has been considered best practice to entirely separate CSS from the content (HTML) and functionality (JavaScript). According to this older school of thought, the goal was to write CSS, HTML, and JavaScript into their separate files.

The philosophy of React is, in fact, the polar opposite of this. Since the separation of CSS, HTML, and JavaScript into separate files did not seem to scale well in larger applications, React bases the division of the application along the lines of its logical functional entities.

The structural units that make up the application's functional entities are React components. A React component defines the HTML for structuring the content, the JavaScript functions for determining functionality, and also the component's styling; all in one place. This is to create individual components that are as independent and reusable as possible.

The code for the final version of our application can be found in the [part2-8](https://github.com/fullstack-hy2020/part2-notes-frontend/tree/part2-8) branch on GitHub.

### Exercises 2.16.-2.17.

#### 2.16: Phonebook step 11

Use the [improved error message](https://fullstackopen.com/en/part2/adding_styles_to_react_app#improved-error-message) example from part 2 as a guide to show a notification that lasts for a few seconds after a successful operation is executed (a person is added or a number is changed):

![Green notification box: Added Arto Vostainen](https://fullstackopen.com/static/767ce348981df266dfa9c0048405a415/5a190/20e.png)

#### 2.17*: Phonebook step 12

Open your application in two browsers. **If you delete a person in browser 1** a short while before attempting to change the person's phone number in browser 2, you will get the following error message:

![Browser console showing a 404 Not Found error](https://fullstackopen.com/static/86794697960655d8d052d197607a505f/5a190/21e.png)

Fix the issue according to the example shown in [promise and errors](https://fullstackopen.com/en/part2/alterting_data_in_server#promise-and-errors) in part 2. Modify the example so that the user is shown a message when the operation does not succeed. The messages for successful and unsuccessful events should look different:

![Red error notification: Information of Edger Dijkstra has already been removed from server](https://fullstackopen.com/static/5c08076628c6827054238e55543c8d19/5a190/22e.png)

**Note** that even if you handle the exception, the first "404" error message is still printed to the console. But you should not see "Uncaught (in promise) Error".

### Couple of important remarks

At the end of this part there are a few more challenging exercises. At this stage, you can skip exercises 2.18-2.20 without too much of a headache, we will come back to the same themes later on.

We have done one thing in our App that is masking a very typical source of error.

We set the state `notes` to have initial value of an empty array:

```javascript
const [notes, setNotes] = useState([])
```

This is a pretty natural initial value since the notes are a set, that is, there are many notes that the state will store.

If the state were only saving "one thing" a more appropriate initial value would be `null`. Since in the beginning there is nothing in the state at the start. Let's see what happens if we use this initial value:

```javascript
const App = () => {
  const [notes, setNotes] = useState(null)
  // ...
}
```

The app breaks down:

![Browser showing React error overlay: Uncaught TypeError: Cannot read properties of null (reading 'map')](https://fullstackopen.com/static/8ad970d473215233157e841269894676/5a190/23e.png)

The error message gives the reason and location for the error. The code that caused the problems is the following:

```javascript
// noteService gets the value of notes
// ...
notes.map(note =>
  <Note key={note.id} note={note} />
)
```

The error message is:

> *Uncaught TypeError: Cannot read properties of null (reading 'map')*

The variable `notes` is `null`, it has been assigned the value of the state `notes`, and then the code tries to call method `map` to a nonexisting object, that is, `null`.

What is the reason for that?

The effect hook using the function `noteService.getAll` sets `notes` to have the notes that the backend is returning:

```javascript
useEffect(() => {
  noteService
    .getAll()
    .then(initialNotes => {
      setNotes(initialNotes)
    })
}, [])
```

However, the problem is that the effect is executed only *after* the first render. And because `notes` has the initial value of null:

```javascript
const App = () => {
  const [notes, setNotes] = useState(null)
```

on the first render the following code gets executed:

```javascript
notes.map(note => ...
```

and this blows up the app since we can not call method `map` of the value `null`.

When we set `notes` to be initially an empty array, there is no error since it is allowed to call map for an empty array.

So, the initialization of the state "masked" the problem that is caused by the fact that the data is not there yet when the code is rendered the first time.

Another way to circumvent the problem is to use conditional rendering and return null if the component state is not properly initialized:

```javascript
const App = () => {
  const [notes, setNotes] = useState(null)

  useEffect(() => {
    noteService
      .getAll()
      .then(initialNotes => {
        setNotes(initialNotes)
      })
  }, [])

  if (!notes) {
    return null
  }

  return (
    // ...
  )
}
```

So on the first render, nothing is rendered. When the notes arrive from the backend, the effect is executed and calls `setNotes`. This causes the component to be rendered again, and at the second render, the notes get rendered to the screen.

The method based on conditional rendering is suitable in cases where it is impossible to define the state so that the initial rendering is possible.

Another thing that we still need to have a closer look at is the second parameter of the useEffect:

```javascript
useEffect(() => {
  // ...
}, [])
```

The second parameter of `useEffect` is used to [specify how often the effect is run](https://react.dev/reference/react/useEffect#parameters). The principle is that the effect is always executed *after* the first render of the component and when the value of the second parameter changes.

If the second parameter is an empty array `[]`, its content never changes and the effect is only run after the first render. This is exactly what we want when initializing the application by fetching data from the server.

However, there are situations where we want to perform the effect at other times, e.g. when the state of the component changes in a particular way.

Let's imagine a simple application for querying currency exchange rates from the Exchange-rate API:

```javascript
import { useState, useEffect } from 'react'
import axios from 'axios'

const App = () => {
  const [value, setValue] = useState('')
  const [rates, setRates] = useState({})
  const [currency, setCurrency] = useState(null)

  useEffect(() => {
    console.log('effect run, currency is now', currency)

    // skip if currency is not defined
    if (currency) {
      console.log('fetching exchange rates...')
      axios
        .get(`https://open.er-api.com/v6/latest/${currency}`)
        .then(response => {
          setRates(response.data.rates)
        })
    }
  }, [currency])

  const handleChange = (event) => {
    setValue(event.target.value)
  }

  const onSearch = (event) => {
    event.preventDefault()
    setCurrency(value)
  }

  return (
    <div>
      <form onSubmit={onSearch}>
        currency: <input value={value} onChange={handleChange} />
        <button type="submit">exchange rate</button>
      </form>
      <pre>
        {JSON.stringify(rates, null, 2)}
      </pre>
    </div>
  )
}

export default App
```

The user interface of the application has a form, in the input field of which the name of the desired currency is written. If the currency exists, the application renders the exchange rates of the currency to the `pre` section.

![Browser showing currency exchange app. Input: eur. JSON output shown below.](https://fullstackopen.com/static/860472e353592395d9a92446f2549a1d/5a190/24e.png)

The application sets the name of the currency entered to the form to the state `currency` at the moment the button is pressed.

When the state `currency` gets a new value, the application fetches its exchange rates from the API in the effect function:

```javascript
const App = () => {
  // ...
  const [currency, setCurrency] = useState(null)

  useEffect(() => {
    console.log('effect run, currency is now', currency)

    if (currency) {
      console.log('fetching exchange rates...')
      axios
        .get(`https://open.er-api.com/v6/latest/${currency}`)
        .then(response => {
          setRates(response.data.rates)
        })
    }
  }, [currency])

  // ...
}
```

The useEffect hook now has `[currency]` as the second parameter. The effect function is therefore executed after the first render, and *always* after the table as its second parameter changes. That is, when the state `currency` gets a new value, the content of the table changes and the effect function is executed.

The condition `if (currency)` is necessary, because `currency` represents a single item. The initial value `null` indicates that there is nothing in the variable. Upon update loop or effect, the program checks first whether a value has been assigned to the variable. The effect has the following condition:

```javascript
if (currency) {
  // exchange rates are fetched
}
```

which prevents requesting the exchange rates just after the first render when the variable `currency` still has the initial value, i.e. a `null` value.

So if the user writes e.g. *eur* in the search field, the application uses Axios to perform an HTTP GET request to the address *https://open.er-api.com/v6/latest/eur* and stores the response in the `rates` state.

When the user then enters another value in the search field, e.g. *usd*, the effect function is executed again and the exchange rates of the new currency are requested for the API.

The way presented here for making API requests might seem a bit awkward. This particular approach is used here just to keep complexity low. It would be better to set the exchange rates in the submit handler function:

```javascript
  const onSearch = (event) => {
    event.preventDefault()
    axios
      .get(`https://open.er-api.com/v6/latest/${value}`)
      .then(response => {
        setRates(response.data.rates)
      })
  }
```

However, there are situations where that technique would not work. For example, you might encounter one such a situation in the exercise 2.20 where the use of useEffect could provide a working solution. We will not quite reach on the approach you selected, e.g. the model solution does not use this trick.

### Exercises 2.18.-2.20.

#### 2.18*: Data for countries, step 1

At [https://studies.cs.helsinki.fi/restcountries/](https://studies.cs.helsinki.fi/restcountries/) you can find a service that offers a lot of information on different countries in a machine-readable format via the REST API. Make an application that allows you to view information from different countries.

The user interface is very simple. The country to be shown is found by typing a search query into the search field.

If there are too many (over 10) countries that match the query, then the user is prompted to make their query more specific:

![Browser showing search field "Sw". Text says "Too many matches, specify another filter"](https://fullstackopen.com/static/d71241198642398451c8672051280387/5a190/19b.png)

If there are ten or fewer countries, but more than one, then all countries matching the query are shown:

![Browser showing search field "Swai". List of countries: Sudan, Swaziland, Sweden, Switzerland.](https://fullstackopen.com/static/eb64826b65349e5d7426615b6d929849/5a190/19c.png)

When there is only one country matching the query, then the basic data of the country (eg. capital and area), its flag and the languages spoken are shown:

![Browser showing search "Switzerland". Details: Capital Bern, Area 41284. Languages list. Flag of Switzerland.](https://fullstackopen.com/static/943183577bd9484b802619623d538645/5a190/19d.png)

**NB**: It is enough that your application works for most countries. Some countries, like *Sudan*, can be hard to support, since the name of the country is part of the name of another country, *South Sudan*. You don't need to worry about these edge cases.

#### 2.19*: Data for countries, step 2

There is still a lot to do in this part, so don't get stuck on this exercise!

Improve on the application in the previous exercise, such that when the names of multiple countries are shown on the page there is a button next to the name of the country, which when pressed shows the view for that country:

![Browser showing list of countries with "show" buttons next to them.](https://fullstackopen.com/static/4c83bd354d6dfc924559c3f5d96c1340/5a190/19e2.png)

In this exercise, it is also enough that your application works for most countries. Countries whose name appears in the name of another country, like *Sudan*, can be ignored.

#### 2.20*: Data for countries, step 3

Add to the view showing the data of a single country, the weather report for the capital of that country. There are dozens of providers for weather data. One suggested API is [https://openweathermap.org/](https://openweathermap.org/). Note that it might take some minutes until a generated API key is valid.

![Browser showing details for Finland. Capital Helsinki. Area 338145. Languages. Flag. Weather in Helsinki section with temperature and icon.](https://fullstackopen.com/static/5688a29a5024d29a531f822941323326/5a190/19f.png)

If you use Open weather map, [here](https://openweathermap.org/weather-conditions#How-to-get-icon-URL) is the description for how to get weather icons.

**NB:** In some browsers (such as Firefox) the chosen API might send an error response, which indicates that HTTPS encryption is not supported, although the request URL starts with `http://`. This issue can be fixed by completing the exercise using Chrome.

**NB:** You need an api-key to use almost every weather service. Do not save the api-key to source control! Nor hardcode the api-key to your source code. Instead use an [environment variable](https://vitejs.dev/guide/env-and-mode.html) to save the key.

Assuming that you are using [Vite](https://vitejs.dev/) to create the application, you can define environment variables in the *.env* file.

```bash
export VITE_SOME_KEY=54l41n3nkuv41m34v41
```

If the file *.env* is at the root of the project, Vite finds the variable:

```bash
export VITE_SOME_KEY=54l41n3nkuv41m34v41 && npm run dev // For Linux/macOS Bash
($env:VITE_SOME_KEY="54l41n3nkuv41m34v41") -and (npm run dev) // For Windows PowerShell
set "VITE_SOME_KEY=54l41n3nkuv41m34v41" && npm run dev // For Windows cmd.exe
```

you can access the value of the key from the `import.meta.env` object:

```javascript
const api_key = import.meta.env.VITE_SOME_KEY
// variable api_key has now the value set in startup
```

**NB:** To prevent accidentally leaking environment variables to the client, only variables prefixed with `VITE_` are exposed to Vite.

Also remember that if you make changes to environment variables, you need to restart the development server for the changes to take effect.

This was the last exercise of this part of the course. It's time to push your code to GitHub and mark all of your finished exercises to the [exercise submission system](https://studies.cs.helsinki.fi/stats/courses/fullstackopen).

***

[Propose changes to material](https://github.com/fullstack-hy2020/fullstack-hy2020.github.io/blob/source/src/content/part2/part2e.md)

| | | |
| :--- | :---: | :--- |
| **Part 2d** [Previous part](https://fullstackopen.com/en/part2/altering_data_in_server) | | **Part 3** [Next part](https://fullstackopen.com/en/part3) |

***

MOOC.fi
