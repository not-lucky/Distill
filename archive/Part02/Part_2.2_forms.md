Fullstack part2 | Forms

---

# **Full Stack Open**

{ ( ) => fs }
About course | Course contents | FAQ | Partners | Challenge
Search from the material | Toggle dark theme | Select language (English)

---

## **Part 2**

### **Forms**

*   [**a** Rendering a collection, modules](https://fullstackopen.com/en/part2/rendering_a_collection_modules)
*   [**b** Forms](https://fullstackopen.com/en/part2/forms)
    *   [Saving the notes in the component state](#saving-the-notes-in-the-component-state)
    *   [Controlled component](#controlled-component)
    *   [Filtering Displayed Elements](#filtering-displayed-elements)
    *   [Exercises 2.6.-2.10.](#exercises-2-6-2-10)
*   [**c** Getting data from server](https://fullstackopen.com/en/part2/getting_data_from_server)
*   [**d** Altering data in server](https://fullstackopen.com/en/part2/altering_data_in_server)
*   [**e** Adding styles to React app](https://fullstackopen.com/en/part2/adding_styles_to_the_react_app)

---

# **b Forms**

Let's continue expanding our application by allowing users to add new notes. You can find the code for our current application [here](https://github.com/fullstack-hy2020/part2-notes/tree/part2-1).

### **Saving the notes in the component state**

To get our page to update when new notes are added it's best to store the notes in the *App* component's state. Let's import the `useState` function and use it to define a piece of state that gets initialized with the initial notes array passed in the props.

```javascript
import { useState } from 'react'
import Note from './components/Note'

const App = (props) => {
  const [notes, setNotes] = useState(props.notes)

  return (
    <div>
      <h1>Notes</h1>
      <ul>
        {notes.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
    </div>
  )
}

export default App
```
copy

The component uses the `useState` function to initialize the piece of state stored in `notes` with the array of notes passed in the props:

```javascript
const App = (props) => {
  const [notes, setNotes] = useState(props.notes)

  // ...
}
```
copy

We can also use React Developer Tools to see that this really happens:

> **[Image Depiction: React Developer Tools]**
> A browser window showing the "Components" tab of React DevTools.
> The `App` component is selected in the left pane.
> In the right "Hooks" pane:
> - **State**: Array(3)
>   - 0: {id: 1, content: "HTML is easy", important: true}
>   - 1: {id: 2, content: "Browser can execute only JavaScript", important: false}
>   - 2: {id: 3, content: "GET and POST are the most important methods of HTTP protocol", important: true}

If we wanted to start with an empty list of notes, we would set the initial value as an empty array, and since the props would not be used, we could omit the `props` parameter from the function definition:

```javascript
const App = () => {
  const [notes, setNotes] = useState([])

  // ...
}
```
copy

Let's stick with the initial value passed in the props for the time being.

Next, let's add an HTML form to the component that will be used for adding new notes.

```javascript
const App = (props) => {
  const [notes, setNotes] = useState(props.notes)

  const addNote = (event) => {
    event.preventDefault()
    console.log('button clicked', event.target)
  }

  return (
    <div>
      <h1>Notes</h1>
      <ul>
        {notes.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
      <form onSubmit={addNote}>
        <input />
        <button type="submit">save</button>
      </form>
    </div>
  )
}
```
copy

We have added the `addNote` function as an event handler to the `form` element that will be called when the form is submitted, by clicking the submit button.

We use the method discussed in [part 1](https://fullstackopen.com/en/part1/a_more_complex_state_debugging_react_apps#handling-arrays) for defining our event handler:

```javascript
const addNote = (event) => {
  event.preventDefault()
  console.log('button clicked', event.target)
}
```
copy

The `event` parameter is the [event](https://developer.mozilla.org/en-US/docs/Web/API/Event) that triggers the call to the event handler function:

The event handler immediately calls the `event.preventDefault()` method, which prevents the default action of submitting a form. The default action would, among other things, cause the page to reload.

The target of the event stored in `event.target` is logged to the console:

> **[Image Depiction: Browser Console]**
> A console log showing:
> `button clicked <form>`
> When expanded, it shows the details of the form element object.

The target in this case is the form that we have defined in our component.

How do we access the data contained in the form's `input` element?

### **Controlled component**

There are many ways to accomplish this; the first method we will take a look at is through the use of so-called [controlled components](https://reactjs.org/docs/forms.html#controlled-components).

Let's add a new piece of state called `newNote` for storing the user-submitted input and let's set it as the `input` element's *value* attribute:

```javascript
const App = (props) => {
  const [notes, setNotes] = useState(props.notes)
  const [newNote, setNewNote] = useState(
    'a new note...'
  )

  const addNote = (event) => {
    event.preventDefault()
    console.log('button clicked', event.target)
  }

  return (
    <div>
      <h1>Notes</h1>
      <ul>
        {notes.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
      <form onSubmit={addNote}>
        <input value={newNote} />
        <button type="submit">save</button>
      </form>
    </div>
  )
}
```
copy

The placeholder text stored as the initial value of the `newNote` state appears in the `input` element, but the input text can't be edited. The console displays a warning that gives us a clue as to what might be wrong:

> **[Image Depiction: Browser Console Error]**
> A console warning message:
> `Warning: You provided a 'value' prop to a form field without an 'onChange' handler. This will render a read-only field. If the field should be mutable use 'defaultValue'. Otherwise, set either 'onChange' or 'readOnly'.`

Since we assigned a piece of the *App* component's state as the *value* attribute of the `input` element, the *App* component now controls the behavior of the input element.

To enable editing of the input element, we have to register an *event handler* that synchronizes the changes made to the input with the component's state:

```javascript
const App = (props) => {
  const [notes, setNotes] = useState(props.notes)
  const [newNote, setNewNote] = useState(
    'a new note...'
  )

  // ...

  const handleNoteChange = (event) => {
    console.log(event.target.value)
    setNewNote(event.target.value)
  }

  return (
    <div>
      <h1>Notes</h1>
      <ul>
        {notes.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
      <form onSubmit={addNote}>
        <input
          value={newNote}
          onChange={handleNoteChange}
        />
        <button type="submit">save</button>
      </form>
    </div>
  )
}
```
copy

We have now registered an event handler to the `onChange` attribute of the form's `input` element:

```javascript
<input
  value={newNote}
  onChange={handleNoteChange}
/>
```
copy

The event handler is called every time a change occurs in the input element. The event handler function receives the event object as its `event` parameter:

```javascript
const handleNoteChange = (event) => {
  console.log(event.target.value)
  setNewNote(event.target.value)
}
```
copy

The `target` property of the event object now corresponds to the controlled `input` element, and `event.target.value` refers to the input value of that element.

Note that we did not need to call the `event.preventDefault()` method like we did in the `onSubmit` event handler. This is because no default action occurs on an input change, unlike a form submission.

You can follow along in the console to see how the state is updated as you type.

> **[Image Depiction: Browser Console showing input logging]**
> The console shows a sequence of logs:
> `a new note...`
> `a new note...s`
> `a new note...se`
> `a new note...sen`
> `a new note...sent`
> Each line corresponds to a character being typed into the input field.

Now that the *newNote* state reflects the current value of the input, we can complete the `addNote` function for creating new notes:

```javascript
const addNote = (event) => {
  event.preventDefault()
  const noteObject = {
    content: newNote,
    important: Math.random() < 0.5,
    id: notes.length + 1,
  }

  setNotes(notes.concat(noteObject))
  setNewNote('')
}
```
copy

First, we create a new object for the note called `noteObject`, which will receive its content from the component's `newNote` state. The identifier for the note is generated based on the total number of notes. This method works for our application since notes are never deleted. With the help of `Math.random()`, our note has a 50% chance of being marked as important.

The new note is added to the list of notes using the `concat` array method, introduced in [part 1](https://fullstackopen.com/en/part1/a_more_complex_state_debugging_react_apps#handling-arrays):

```javascript
setNotes(notes.concat(noteObject))
```
copy

The method does not mutate the original `notes` state array, but rather creates a *new copy of the list* with the new item added to the end. This is important since we must [never mutate state](https://fullstackopen.com/en/part1/a_more_complex_state_debugging_react_apps#rules-of-hooks) directly in React!

The event handler also resets the value of the controlled input element by calling the `setNewNote` function of the `newNote` state:

```javascript
setNewNote('')
```
copy

You can find the code for our current application [here](https://github.com/fullstack-hy2020/part2-notes/tree/part2-2).

### **Filtering Displayed Elements**

Let's add some new functionality to our application that allows us to view only the important notes.

Let's add a piece of state to the *App* component that keeps track of which notes should be displayed:

```javascript
const App = (props) => {
  const [notes, setNotes] = useState(props.notes)
  const [newNote, setNewNote] = useState('')
  const [showAll, setShowAll] = useState(true)

  // ...
}
```
copy

Let's change the component so that it stores a list of all the notes to be displayed in the `notesToShow` variable. The items of the list depend on the state of the component:

```javascript
const App = (props) => {
  // ...
  const [showAll, setShowAll] = useState(true)

  // ...

  const notesToShow = showAll
    ? notes
    : notes.filter(note => note.important === true)

  return (
    <div>
      <h1>Notes</h1>
      <ul>
        {notesToShow.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
      {/* ... */}
    </div>
  )
}
```
copy

The definition of the `notesToShow` variable is rather compact:

```javascript
const notesToShow = showAll
  ? notes
  : notes.filter(note => note.important === true)
```
copy

If the value of `showAll` is true, the `notesToShow` variable will be assigned the value of the entire `notes` array. If `showAll` is false, `notesToShow` will be assigned an array that only contains the notes that have their `important` property set to true.

Filtering is done with the help of the array [filter](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter) method. The comparison operator used in the comparison is actually redundant, since the value of `note.important` is either `true` or `false`, which means we can simply write:

```javascript
notes.filter(note => note.important)
```
copy

We used the [conditional](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Conditional_Operator) operator in the definition of the `notesToShow` variable. The operator is common in many other programming languages as well.

The operator works as follows:

```javascript
const result = condition ? val1 : val2
```
copy

The `result` variable will be set to the value of `val1` if `condition` is `true`. If `condition` is `false`, the `result` variable will be set to the value of `val2`.

Next, let's add functionality that enables the user to toggle the `showAll` state of the application from the user interface.

The relevant changes are shown below:

```javascript
import { useState } from 'react'
import Note from './components/Note'

const App = (props) => {
  const [notes, setNotes] = useState(props.notes)
  const [newNote, setNewNote] = useState('')
  const [showAll, setShowAll] = useState(true)

  // ...

  return (
    <div>
      <h1>Notes</h1>
      <div>
        <button onClick={() => setShowAll(!showAll)}>
          show {showAll ? 'important' : 'all' }
        </button>
      </div>
      <ul>
        {notesToShow.map(note =>
          <Note key={note.id} note={note} />
        )}
      </ul>
      {/* ... */}
    </div>
  )
}
```
copy

The displayed notes (all versus important) are controlled with a button. The event handler for the button is so simple that it has been defined directly in the attributes of the button element. The event handler switches the value of `showAll` from true to false and vice-versa:

```javascript
() => setShowAll(!showAll)
```
copy

The text of the button depends on the value of the `showAll` state:

```javascript
show {showAll ? 'important' : 'all'}
```
copy

You can find the code for our current application [here](https://github.com/fullstack-hy2020/part2-notes/tree/part2-3).

### **Exercises 2.6.-2.10.**

In the first few exercises, we will start working on an application that will be further developed in the later exercises. In the finished application, different parts of the application will be separated into their own components. However, you can maintain all of the components in a single file for now.

The application could be used for maintaining a phonebook.

#### **2.6: The Phonebook Step 1**

Let's create a simple phonebook. In this part, we will only be adding names to the phonebook.

Let's start by implementing the addition of a person to phonebook.

You can use the following code as a starting point for the *App* component:

```javascript
import { useState } from 'react'

const App = () => {
  const [persons, setPersons] = useState([
    { name: 'Arto Hellas' }
  ])
  const [newName, setNewName] = useState('')

  return (
    <div>
      <h2>Phonebook</h2>
      <form>
        <div>
          name: <input />
        </div>
        <div>
          <button type="submit">add</button>
        </div>
      </form>
      <h2>Numbers</h2>
      ...
    </div>
  )
}

export default App
```
copy

The `newName` state is meant for controlling the form `input` element.

Sometimes it can be beneficial to render the state and other variables as text for debugging purposes. You can temporarily add the following element to the rendered component:

```javascript
<div>debug: {newName}</div>
```
copy

It's also important to put what we learned in the [debugging React applications](https://fullstackopen.com/en/part1/a_more_complex_state_debugging_react_apps#debugging-react-applications) chapter of part 1 into good use. The [React developer tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbhfkeoomphohobi) extension is especially useful for tracking changes in the application's state.

After finishing this exercise, the application should look something like this:

> **[Image Depiction: Phonebook UI]**
> A web page with the header "Phonebook".
> A label "name:" followed by an input field containing "Arto Hellas".
> An "add" button.
> A header "Numbers".
> A list showing "Arto Hellas".

Note that the use of the name of the person as the `key` value of the list items is fine in this case, as names will be unique in our phonebook.

#### **2.7: The Phonebook Step 2**

Prevent the user from being able to add names that already exist in the phonebook. JavaScript arrays have numerous suitable [methods](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) for accomplishing this task. Keep in mind [how object equality works](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/is) in Javascript.

Issue a warning with the [alert](https://developer.mozilla.org/en-US/docs/Web/API/Window/alert) command when such an action is attempted:

> **[Image Depiction: Browser Alert Dialog]**
> An alert box at the top of the browser saying:
> `Arto Hellas is already added to phonebook`
> With an "OK" button.

*Hint:* when you are forming an object that is to be added to the `persons` array, the command `console.log(newName)` will be helpful during the process.

#### **2.8: The Phonebook Step 3**

Expand your application by allowing users to add phone numbers to the phonebook. You will need to add a second `input` element to the form (along with its own event handler):

```javascript
<form>
  <div>name: <input /></div>
  <div>number: <input /></div>
  <div><button type="submit">add</button></div>
</form>
```
copy

At this point, the application could look something like this. The image also displays the application's state with the help of [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbhfkeoomphohobi):

> **[Image Depiction: Phonebook UI with Numbers and DevTools]**
> The UI shows names and phone numbers:
> - Arto Hellas 040-123456
> - Ada Lovelace 39-44-5323523
> - Dan Abramov 12-43-234345
> - Mary Poppendieck 39-23-6423122
>
> The DevTools pane shows the `App` state as an array of 4 objects, each with `name` and `number` properties.

#### **2.9: The Phonebook Step 4**

Implement a search field that can be used to filter the list of people by name:

> **[Image Depiction: Phonebook UI with Search Filter]**
> A "filter shown with" input field containing "ada".
> The list below shows only "Ada Lovelace 39-44-5323523".

You can implement the search field as an `input` element that is placed outside the HTML form. The filtering logic shown in the [filtering displayed elements](#filtering-displayed-elements) section can be used as a starting point.

#### **2.10: The Phonebook Step 5**

If you have implemented your code for the whole application in this session in the *App* component, refactor it by extracting the suitable parts into new components. Maintain the application's state and all event handlers in the *App* root component.

It is sufficient to extract three components. The structure of the finished application could look like this:

```javascript
const App = () => {
  // ...

  return (
    <div>
      <h2>Phonebook</h2>

      <Filter ... />

      <h3>Add a new</h3>

      <PersonForm ... />

      <h3>Numbers</h3>

      <Persons ... />
    </div>
  )
}
```
copy

*Note:* Passing state and event handlers as props to the extracted components is discussed in [part 1](https://fullstackopen.com/en/part1/a_more_complex_state_debugging_react_apps#passing-state-to-child-components).

---

[Improve this page](https://github.com/fullstack-hy2020/fullstack-hy2020.github.io/edit/master/src/content/part2/en/part2b.md)

---
[**< Previous**](https://fullstackopen.com/en/part2/rendering_a_collection_modules) | [**Next >**](https://fullstackopen.com/en/part2/getting_data_from_server)
