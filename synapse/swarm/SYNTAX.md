## Lift
  Supported comparisons: Basic

Lift all foo tufos.

    foo

Lift all foo tufos from cortexes tagged my.core

    my.core/foo

Lift all foo tufos with a foo:bar prop with the given value.

    foo:bar=10
    foo:bar="ten"

## Must/Cant
Supported comparisons: Basic Extended

Remove all tufos from our data set that do not have a foo:baz prop.

    ... +foo:baz

Remove all tufos from our data set that have a foo:baz prop.

    ... -foo:baz

Remove all tufos from our data set that do not have a foo:baz prop equal to the given value

    ... +foo:baz=10
    ... +foo:baz="ten"

Remove all tufos from our data set that have a foo:baz prop equal to the given value

    ... -foo:baz=10
    ... -foo:baz="ten"

## Join
Supported comparisons: Basic

Join all foo tufos whose foo:bar prop matches a baz:faz prop in our data set.

    ... [foo:bar=baz:faz

Join all foo tufos whose foo:bar prop matches a foo:bar prop in our data set.

    ... [foo:bar

## Basic Comparisons
Greater Than

    foo:bar>10
    foo:bar>"ten"

Greater Than Equals

    foo:bar>=10
    foo:bar>="ten"

Equals

    foo:bar=10
    foo:bar="ten"

Less Than Equals

    foo:bar<=10
    foo:bar<="ten"

Less Than

    foo:bar<10
    foo:bar<"ten"

Regular Expression

    foo:bar~="^foo"

## Extended Comparisons

Value In Range
range(x,y) is equivalent to x <= value < y

    foo:bar*range=(1,2)
    foo:bar*range=("one","two")

Value In Set

    foo:bar*in=(1,2)
    foo:bar*in=("one","two")

## Logical Operations

And

    ... &foo:bar=10 
    
Or

    ... |foo:bar=10 
