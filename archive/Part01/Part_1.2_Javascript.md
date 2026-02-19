`[{ } => fs]` **About course** **Course contents** **FAQ** **Partners** **Challenge** (Search) (Toggle theme) **English** (Change language)

---

*[A light green banner with geometric line drawings of a cube and circles.]*
**FullStack** / Part 1 / **JavaScript**

---


- a Introduction to React
- **b JavaScript**
  - Variables
  - Arrays
  - Objects
  - Functions
  - Exercises 1.3.-1.5.
  - Object methods and "this"
  - Classes
  - Javascript materials
- c Component state, event handlers
- d A more complex state, debugging React apps

---

# (b) JavaScript

During the course, we have a goal and a need to learn a sufficient amount of JavaScript in addition to web development.

JavaScript has advanced rapidly in the last few years and in this course, we use features from the newer versions. The official name of the JavaScript standard is [ECMAScript](https://tc39.es/ecma262/). At this moment, the latest version is the one released in June of 2024 with the name [ECMAScript® 2024](https://tc39.es/ecma262/), otherwise known as ES15.

Browsers do not yet support all of JavaScript's newest features. Due to this fact, a lot of code run in browsers has been transpiled from a newer version of JavaScript to an older, more compatible version.

Today, the most popular way to do transpiling is by using [Babel](https://babeljs.io/). Transpilation is automatically configured in React applications created with Vite. We will take a closer look at the configuration of the transpilation in [part 7](https://fullstackopen.com/en/part7) of this course.

[Node.js](https://nodejs.org/en/) is a JavaScript runtime environment based on Google's [Chrome V8](https://v8.dev/) JavaScript engine and works practically anywhere - from servers to mobile phones. Let's practice writing some JavaScript using Node. The latest versions of Node already understand the latest versions of JavaScript, so the code does not need to be transpiled.

The code is written into files ending with *.js* that are run by issuing the command `node name_of_file.js`.

It is also possible to write JavaScript code into the Node.js console, which is opened by typing `node` in the command line, as well as into the browser's developer tool console. [The newest revisions of Chrome handle the newer features of JavaScript pretty well](https://kangax.github.io/compat-table/es6/) without transpiling the code. Alternatively, you can use a tool like [JS Bin](https://jsbin.com/).

JavaScript is sort of reminiscent, both in name and syntax, to Java. But when it comes to the core mechanism of the language they could not be more different. Coming from a Java background, the behavior of JavaScript can seem a bit alien, especially if one does not make the effort to look up its features.

In certain circles, it has also been popular to attempt "simulating" Java features and design patterns in JavaScript. We do not recommend doing this as the languages and respective ecosystems are ultimately very different.

### Variables

In JavaScript there are a few ways to go about defining variables:

```javascript
const x = 1
let y = 5

console.log(x, y)   // 1 5 are printed
y += 10
console.log(x, y)   // 1 15 are printed
y = 'sometext'
console.log(x, y)   // 1 sometext are printed
x = 4               // causes an error
```

`const` does not define a variable but a *constant* for which the value can no longer be changed. On the other hand, `let` defines a normal variable.

In the example above, we also see that the variable's data type can change during execution. At the start, `y` stores an integer; at the end, it stores a string.

It is also possible to define variables in JavaScript using the keyword `var`. For a long time, var was the only way to define variables. The keywords const and let were introduced in 2015 with the release of ES6. In specific situations, var works in a different way compared to variable definitions in most languages - see [JavaScript Variables - Should You Use let, var or const? on Medium](https://medium.com/javascript-scene/javascript-es6-var-let-or-const-ba58b8dcde75) or [var vs let vs const in JS](https://ui.dev/var-let-const/) for more information. During this course the use of var is ill-advised and you should stick with using const and let! You can find more on this topic on YouTube - e.g. [var, let and const - ES6 JavaScript Features](https://www.youtube.com/watch?v=sjyJBL5fkp8).

### Arrays

An [array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) and a couple of examples of its use:

```javascript
const t = [1, -1, 3]

t.push(5)

console.log(t.length) // 4 is printed
console.log(t[1])     // -1 is printed

t.forEach(value => {
  console.log(value)  // numbers 1, -1, 3, 5 are printed, each on its own line
})
```

Notable in this example is the fact that although a variable declared with const cannot be changed, the contents of the array can. Because the object is an array, the contents of the array can be modified. This is because the const declaration ensures the immutability of the reference itself, not the data it points to. Think of it like changing the furniture inside a house, while the address of the house remains the same.

One way of iterating through the items of the array is using `forEach` as seen in the example. `forEach` receives a *function* defined using the arrow syntax as a parameter.

```javascript
value => {
  console.log(value)
}
```

forEach calls the function for each of the items in the array, always passing the individual item as an argument. The function as the argument of forEach may also receive [other arguments](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach).

In the previous example, a new item was added to the array using the method [push](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/push). When using React, techniques from functional programming are often used. One characteristic of the functional programming paradigm is the use of [immutable](https://en.wikipedia.org/wiki/Immutable_object) data structures. In React code, it is preferable to use the method [concat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/concat), which creates a new array with the added item. This ensures the original array remains unchanged.

```javascript
const t = [1, -1, 3]

const t2 = t.concat(5)  // creates new array

console.log(t)  // [1, -1, 3] is printed
console.log(t2) // [1, -1, 3, 5] is printed
```

The method call `t.concat(5)` does not add a new item to the old array but returns a new array which, besides containing the items of the old array, also contains the new item.

There are plenty of useful methods defined for arrays. Let's look at a short example of using the [map](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map) method.

```javascript
const t = [1, 2, 3]

const m1 = t.map(value => value * 2)
console.log(m1)   // [2, 4, 6] is printed
```

Based on the old array, map creates a *new array*, for which the function given as a parameter is used to create the items. In the case of this example, the original value is multiplied by two.

Map can also transform the array into something completely different:

```javascript
const m2 = t.map(value => '<li>' + value + '</li>')
console.log(m2)
// [ '<li>1</li>', '<li>2</li>', '<li>3</li>' ] is printed
```

Here an array filled with integer values is transformed into an array containing strings of HTML using the map method. In [part 2](https://fullstackopen.com/en/part2) of this course, we will see that map is used quite frequently in React.

Individual items of an array are easy to assign to variables with the help of the [destructuring assignment](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment).

```javascript
const t = [1, 2, 3, 4, 5]

const [first, second, ...rest] = t

console.log(first, second)  // 1 2 is printed
console.log(rest)           // [3, 4, 5] is printed
```

Above, the variable `first` is assigned the first integer of the array and the variable `second` is assigned the second integer of the array. The variable `rest` "collects" the remaining integers into its own array.

### Objects

There are a few different ways of defining objects in JavaScript. One very common method is using [object literals](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Grammar_and_types#Object_literals), which happens by listing its properties within braces:

```javascript
const object1 = {
  name: 'Arto Hellas',
  age: 35,
  education: 'PhD',
}

const object2 = {
  name: 'Full Stack web application development',
  level: 'intermediate studies',
  size: 5,
}

const object3 = {
  name: {
    first: 'Dan',
    last: 'Abramov',
  },
  grades: [2, 3, 5, 3],
  department: 'Stanford University',
}
```

The values of the properties can be of any type, like integers, strings, arrays, objects...

The properties of an object are referenced by using the "dot" notation, or by using brackets:

```javascript
console.log(object1.name)         // Arto Hellas is printed
const fieldName = 'age'
console.log(object1[fieldName])   // 35 is printed
```

You can also add properties to an object on the fly by either using dot notation or brackets:

```javascript
object1.address = 'Helsinki'
object1['secret number'] = 12341
```

The latter of the additions has to be done by using brackets because when using dot notation, *secret number* is not a valid property name because of the space character.

Naturally, objects in JavaScript can also have methods. However, during this course, we do not need to define any objects with methods of their own. This is why they are only discussed briefly during the course.

Objects can also be defined using so-called *constructor functions*, which results in a mechanism reminiscent of many other programming languages, e.g. Java's classes. Despite this similarity, JavaScript does not have classes in the same sense as object-oriented programming languages. There has been, however, the addition of the *class* syntax starting from version ES6, which in some cases helps structure object-oriented classes.

### Functions

We have already become familiar with defining arrow functions. The complete process, without cutting corners, of defining an arrow function is as follows:

```javascript
const sum = (p1, p2) => {
  console.log(p1)
  console.log(p2)
  return p1 + p2
}
```

and the function is called as can be expected:

```javascript
const result = sum(1, 5)
console.log(result)
```

If there is just a single parameter, we can exclude the parentheses from the definition:

```javascript
const square = p => {
  console.log(p)
  return p * p
}
```

If the function only contains a single expression then the braces are not needed. In this case, the function only returns the result of its only expression. Now, if we remove console printing, we can further shorten the function definition:

```javascript
const square = p => p * p
```

This form is particularly handy when manipulating arrays - e.g. when using the map method:

```javascript
const t = [1, 2, 3]
const tSquared = t.map(p => p * p)
// tSquared is now [1, 4, 9]
```

The arrow function feature was added to JavaScript in 2015, with version [ES6](http://es6-features.org/#ArrowFunctions). Before this, the only way to define functions was by using the keyword `function`.

There are two ways to reference the function; one is giving a name in a [function declaration](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/function).

```javascript
function product(a, b) {
  return a * b
}

const result = product(2, 6)
// result is now 12
```

The other way to define the function is by using a [function expression](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/function). In this case, there is no need to give the function a name and the definition may reside among the rest of the code:

```javascript
const average = function(a, b) {
  return (a + b) / 2
}

const result = average(2, 5)
// result is now 3.5
```

During this course, we will define all functions using the arrow syntax.

---

### Exercises 1.3.-1.5.

We continue building the application that we started working on in the previous exercises. You can write the code into the same project since we are only interested in the final state of the submitted application.

> **Pro-tip:** you may run into issues when it comes to the structure of the props that components receive. A good way to make things more clear is by printing the props to the console, e.g. as follows:

```javascript
const Header = (props) => {
  console.log(props)
  return <h1>{props.course}</h1>
}
```

**If and when you encounter an error message**
> Objects are not valid as a React child

keep in mind the things told [here](https://fullstackopen.com/en/part1/javascript#objects).

#### 1.3: Course Information step 3

Let's move forward to using objects in our application. Modify the variable definitions of the *App* component as follows and also refactor the application so that it still works:

```javascript
const App = () => {
  const course = 'Half Stack application development'
  const part1 = {
    name: 'Fundamentals of React',
    exercises: 10
  }
  const part2 = {
    name: 'Using props to pass data',
    exercises: 7
  }
  const part3 = {
    name: 'State of a component',
    exercises: 14
  }

  return (
    <div>
      ...
    </div>
  )
}
```

#### 1.4: Course Information step 4

Place the objects into an array. Modify the variable definitions of *App* into the following form and modify the other parts of the application accordingly:

```javascript
const App = () => {
  const course = 'Half Stack application development'
  const parts = [
    {
      name: 'Fundamentals of React',
      exercises: 10
    },
    {
      name: 'Using props to pass data',
      exercises: 7
    },
    {
      name: 'State of a component',
      exercises: 14
    }
  ]

  return (
    <div>
      ...
    </div>
  )
}
```

> **NB** at this point you can assume that there are always three items, so there is no need to go through the arrays using loops. We will come back to the topic of rendering components based on items in arrays with a more thorough exploration in the [next part of the course](https://fullstackopen.com/en/part2).

However, do not pass different objects as separate props from the App component to the components *Content* and *Total*. Instead, pass them directly as an array:

```javascript
const App = () => {
  // const definitions

  return (
    <div>
      <Header course={course} />
      <Content parts={parts} />
      <Total parts={parts} />
    </div>
  )
}
```

#### 1.5: Course Information step 5

Let's take the changes one step further. Change the course and its parts into a single JavaScript object. Fix everything that breaks.

```javascript
const App = () => {
  const course = {
    name: 'Half Stack application development',
    parts: [
      {
        name: 'Fundamentals of React',
        exercises: 10
      },
      {
        name: 'Using props to pass data',
        exercises: 7
      },
      {
        name: 'State of a component',
        exercises: 14
      }
    ]
  }

  return (
    <div>
      ...
    </div>
  )
}
```

---

### Object methods and "this"

Because this course uses a version of React containing React Hooks we do not need to define objects with methods. The contents of this chapter are not relevant to the course but are certainy in many ways good to know. In particular, when using older versions of React one must understand the topics of this chapter.

Arrow functions and functions defined using the `function` keyword vary substantially when it comes to how they behave with respect to the keyword [this](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this), which refers to the object itself.

We can assign methods to an object by defining properties that are functions:

```javascript
const arto = {
  name: 'Arto Hellas',
  age: 35,
  education: 'PhD',
  greet: function() {
    console.log('Hello, my name is ' + this.name)
  },
}

arto.greet()  // "Hello, my name is Arto Hellas" gets printed
```

Methods can be assigned to objects even after the creation of the object:

```javascript
const arto = {
  name: 'Arto Hellas',
  age: 35,
  education: 'PhD',
  greet: function() {
    console.log('Hello, my name is ' + this.name)
  },
}

arto.growOlder = function() {
  this.age += 1
}

console.log(arto.age)   // 35 is printed
arto.growOlder()
console.log(arto.age)   // 36 is printed
```

Let's slightly modify the object:

```javascript
const arto = {
  name: 'Arto Hellas',
  age: 35,
  education: 'PhD',
  greet: function() {
    console.log('Hello, my name is ' + this.name)
  },
  doAddition: function(a, b) {
    console.log(a + b)
  },
}

arto.doAddition(1, 4)        // 5 is printed

const referenceToAddition = arto.doAddition
referenceToAddition(10, 15)   // 25 is printed
```

Now the object has the method `doAddition` which calculates the sum of numbers given to it as parameters. The method is called in the usual way, using the object `arto.doAddition(1, 4)` or by storing a method reference in a variable and calling the method through the variable: `referenceToAddition(10, 15)`.

If we try to do the same with the method `greet` we run into an issue:

```javascript
arto.greet()       // "Hello, my name is Arto Hellas" gets printed

const referenceToGreet = arto.greet
referenceToGreet() // prints "Hello, my name is undefined"
```

When calling the method through a reference, the method loses knowledge of what the original `this` was. Contrary to other languages, in JavaScript the value of `this` is defined based on *how the method is called*. When calling the method through a reference, the value of `this` becomes the so-called [global object](https://developer.mozilla.org/en-US/docs/Glossary/Global_object) and the end result is often not what the software developer had originally intended.

Losing track of `this` when writing JavaScript code brings forth a few potential issues. Situations often arise where React or Node (or more specifically the JavaScript engine of the web browser) needs to call some method in an object that the developer has defined. However, in this course, we avoid these issues by using "this-less" JavaScript.

One situation leading to the "disappearance" of `this` arises when we set a timeout to call the `greet` function on the `arto` object, using the [setTimeout](https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/setTimeout) function.

```javascript
const arto = {
  name: 'Arto Hellas',
  greet: function() {
    console.log('Hello, my name is ' + this.name)
  },
}

setTimeout(arto.greet, 1000)
```

As mentioned previously, the value of `this` in JavaScript is defined based on how the method is being called. When `setTimeout` is calling the method, it is the JavaScript engine that actually calls the method and, at that point, `this` refers to the global object.

There are several mechanisms by which the original `this` can be preserved. One of these is using a method called [bind](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/bind):

```javascript
setTimeout(arto.greet.bind(arto), 1000)
```

Calling `arto.greet.bind(arto)` creates a new function where `this` is bound to point to Arto, independent of where and how the method is being called.

Using arrow functions it is possible to solve some of the problems related to `this`. They should not, however, be used as methods for objects because then `this` does not work at all. We will come back later to the behavior of `this` in relation to arrow functions.

If you want to gain a better understanding of how `this` works in JavaScript, the Internet is full of material about the topic, e.g. the screencast series [Understand JavaScript's this Keyword in Depth](https://egghead.io/courses/understand-javascript-s-this-keyword-in-depth) by [egghead.io](https://egghead.io/) is highly recommended!

### Classes

As mentioned previously, there is no class mechanism in JavaScript like the ones in object-oriented programming languages. There are, however, features to make "simulating" object-oriented [classes](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes) possible.

Let's take a quick look at the class syntax that was introduced into JavaScript with ES6, which substantially simplifies the definition of classes (or class-like things) in JavaScript.

In the following example we define a "class" called Person and two Person objects:

```javascript
class Person {
  constructor(name, age) {
    this.name = name
    this.age = age
  }
  greet() {
    console.log('Hello, my name is ' + this.name)
  }
}

const adam = new Person('Adam Ondra', 29)
adam.greet()

const janja = new Person('Janja Garnbret', 23)
janja.greet()
```

When it comes to syntax, JavaScript classes and the instances created from them are very reminiscent of how classes and objects work in Java. Their behavior is also quite similar to Java objects. At their core, however, they are still plain JavaScript objects built on [prototypal inheritance](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Inheritance_and_the_prototype_chain). The type of any such class instance is still `object`, because JavaScript fundamentally defines only a limited set of types: [Boolean, Null, Undefined, Number, String, Symbol, BigInt, and Object](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Data_structures).

The introduction of the class syntax was a controversial addition. Check out [Not Awesome: ES6 Classes](https://github.com/getify/You-Dont-Know-JS/blob/1st-ed/es6%20%26%20beyond/ch3.md#classes) or [Is "Class" in ES6 The New "Bad" Part?](https://medium.com/@rajaraodv/is-class-in-es6-the-new-bad-part-6c4e6fe1ee65) on Medium for more details.

The ES6 class syntax is used a lot in "old" React and also in Node.js, hence an understanding of it is beneficial even in this course. However, since we are using the new [Hooks](https://reactjs.org/docs/hooks-intro.html) feature of React throughout this course, we have no concrete use for JavaScript's class syntax.

### Javascript materials

There exist both good and poor guides for JavaScript on the Internet. Most of the links on this page relating to JavaScript features reference [Mozilla's JavaScript Guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide).

It is highly recommended to immediately read [JavaScript language overview](https://developer.mozilla.org/en-US/docs/Web/JavaScript/A_re-introduction_to_JavaScript) on Mozilla's website.

If you wish to get to know JavaScript deeply there is a great free book series on the Internet called [You-Dont-Know-JS](https://github.com/getify/You-Dont-Know-JS).

Another great resource for learning JavaScript is [javascript.info](https://javascript.info/).

The free and highly engaging book [Eloquent JavaScript](https://eloquentjavascript.net/) takes you from the basics to interesting stuff quickly. It is a mixture of theory, projects and exercises and covers general programming theory as well as the JavaScript language.

[Namaste 🙏 JavaScript](https://www.youtube.com/playlist?list=PLlasXeu85E9cQ32gLCvAvr9vNaUccPVNP) is another great and highly recommended free JavaScript tutorial in order to understand how JS works under the hood. Namaste JavaScript is a pure in-depth JavaScript course released for free on YouTube. It will cover the core concepts of JavaScript in detail and everything about how JS works behind the scenes inside the JavaScript engine.

[egghead.io](https://egghead.io/) has plenty of quality screencasts on JavaScript, React, and other interesting topics. Unfortunately, some of the material is behind a paywall.

---

[Propose changes to material](https://github.com/fullstack-hy2020/fullstack-hy2020.github.io/edit/master/src/content/part1/part1b.md)

**Part 1a**
Previous part

**Part 1c**
Next part

*[University of Helsinki Logo]*
