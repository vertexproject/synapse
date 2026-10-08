<a id="storm-adv-classes"></a>

# Storm Reference - Advanced - Classes

Storm supports user defined **classes**, which bundle a set of [functions](storm_adv_functions.md#storm-adv-functions) together with the state they operate on. Classes are most useful in Storm packages, where a power-up can hand an analyst or another module an object with a small, well defined set of methods instead of a bare dictionary.

> [!NOTE]
> A class instance holds working state for the code using it, such as a running count, a buffer of items waiting to be sent, or a client for an external API. Information about the things being analyzed belongs in the graph as nodes, properties and tags, not in class instances.

<a id="storm-class-declare"></a>

## Declaring Classes

A class is declared with the `class` keyword and contains one or more **methods**, each declared with the `method` keyword. A method is a function which is bound to an instance of the class. This `Tally` class counts how many times it has seen each key:

```storm
class Tally {

    method __storm_init() {
        $self.counts = ({})
        return()
    }

    method add(key) {
        $self.counts.$key = ($self.count($key) + 1)
        return()
    }

    method count(key) {
        $valu = $self.counts.$key
        if ($valu = null) { return((0)) }
        return($valu)
    }
}
```

A class body may contain **only** method declarations.

<a id="storm-class-instance"></a>

## Creating Instances

Declaring a class binds its name as a variable holding a constructor. Calling that constructor creates an **instance**. Each call produces a new instance with its own state. Methods are invoked, and instance values are read and set, using the same dot notation used elsewhere in Storm.

Given a few FQDN nodes:

A `Tally` instance can count them by zone as they pass through the pipeline:

```storm
class Tally {

    method __storm_init() {
        $self.counts = ({})
        return()
    }

    method add(key) {
        $self.counts.$key = ($self.count($key) + 1)
        return()
    }

    method count(key) {
        $valu = $self.counts.$key
        if ($valu = null) { return((0)) }
        return($valu)
    }
}

$tally = $Tally()

inet:fqdn:zone
$tally.add(:zone)
| spin |

$lib.print(`vertex.link={$tally.count(vertex.link)} woot.com={$tally.count(woot.com)}`)
$lib.print($tally.counts)
```

Output:

```stormdoc
vertex.link=3 woot.com=2
{'vertex.link': 3, 'woot.com': 2}
```

<a id="storm-class-self"></a>

## \$self

Within a method, `$self` refers to the instance the method was called on. Instance state is created by assigning to `$self`, most often in `__storm_init()`.

`$self` and `$super` are not variables. They are provided by the method while it runs, and may only be used by code written within the method body, including a function declared inside it. Once the method returns, a function declared inside it may no longer use them. Passing `$self` somewhere else, such as returning it or handing it to a callback, passes the instance itself, which gives access only to its public methods and values. `$self` and `$super` may not be assigned to, may not be used in the parameters of a method, and are not available within an embedded query such as `${ }`. Outside of a class they remain ordinary variable names.

A method is found before a value of the same name, and a value may not be set with the name of a method.

A **public** value, one whose name does not begin with `__`, may be freely read and modified from outside the class. Any code holding the instance may replace a public value, change one in place, or add a new one, without calling a method, and the class is not told when it does. A class should not rely on a public value keeping what its methods set: keep such state [private](#storm-class-private), and provide a method for callers who need to read it.

Here code outside the class replaces the count a `Counter` keeps, and adds a value of its own:

```storm
class Counter {

    method __storm_init() {
        $self.count = (0)
        return()
    }

    method add() {
        $self.count = ($self.count + 1)
        return()
    }
}

$counter = $Counter()
$counter.add()

$counter.count = (100)
$counter.note = "set from outside the class"

$lib.print(`count={$counter.count} note={$counter.note}`)
```

Output:

```stormdoc
count=100 note=set from outside the class
```

<a id="storm-class-lifecycle"></a>

## Constructors and Cleanup

Methods whose names begin with `__storm_` are **built-in** methods which the runtime invokes itself. The prefix is reserved: a class may only declare the built-in methods listed below, and an instance value may not use it. Currently there are two:

- `__storm_init()` is the **constructor**. It runs when an instance is created, and the arguments passed to the constructor are passed to it. A class with no `__storm_init()`, whether its own or one inherited from the class it extends, takes no constructor arguments.
- `__storm_fini()` is the **cleanup** method. It runs once, when the instance is **finalized**.

Every instance also provides a built-in `fini()` method, which finalizes it. Because `fini` names this built-in, a class may not declare a method named `fini()` and an instance value may not be named `fini`.

An instance is finalized when `fini()` is called on it, or otherwise when the query in which its class was declared or imported finishes. A `view.exec` or `runas` block counts as its own query, so an instance of a class declared inside one is finalized when the block ends. Reassigning or dropping a variable which holds an instance does not finalize it. Instances which were never explicitly finalized are finalized in reverse order of construction as the query finishes, and output from their `__storm_fini()` methods is still delivered to the caller. An instance whose construction fails is never finalized, so a constructor which acquires a resource before failing should release it before it raises. An instance may not be finalized while it is being constructed.

This `Batcher` collects items and sends them to a queue in batches. Its `__storm_fini()` method sends whatever is left, so the last partial batch is never lost, even though nothing in the query calls `flush()` for it:

```storm
class Batcher {

    method __storm_init(name as str, size as int=(3)) {
        $self.size = $size
        $self.__queue = $lib.queue.gen($name)
        $self.__items = ([])
        return()
    }

    method add(item) {
        $self.__items.append($item)
        if ($lib.len($self.__items) >= $self.size) { $self.flush() }
        return()
    }

    method flush() {
        if $self.__items {
            $self.__queue.puts($self.__items)
            $lib.print(`sent {$lib.len($self.__items)} items`)
            $self.__items = ([])
        }
        return()
    }

    method __storm_fini() {
        $self.flush()
        return()
    }
}

$batch = $Batcher(example.batch)
for $fqdn in (vertex.link, woot.com, newp.com, foo.com, bar.com) {
    $batch.add($fqdn)
}
$lib.print("the query is finishing")
```

Output:

```stormdoc
sent 3 items
the query is finishing
sent 2 items
```

Once finalized, an instance may no longer be used: reading or setting a value on it, or calling one of its methods, raises an error. Calling `fini()` again has no effect.

Any code holding an instance may call its `fini()`, and each `__storm_fini()` runs with the [privileges](#storm-class-privileges) of the code which declared it, so a caller may run the cleanup of an instance a privileged module handed it. A module should not hand out an instance it keeps using itself, such as one held in a module variable. Hand out a new instance instead.

> [!NOTE]
> A query which constructs many instances of a class with a `__storm_fini()` method, such as one which runs for a long time or constructs them in a loop, holds every instance until the query finishes, even once nothing refers to it. This includes a dmon or a cron job which runs a long query. Call `fini()` on each instance once it is no longer needed.

<a id="storm-class-private"></a>

## Private Methods and Values

A method or instance value whose name begins with a double underscore ( `__` ) is **private**. It may be used from within the class through `$self`, but not from outside it. A value without the prefix is public, and may be modified from outside the class. This is the same convention used for [module](storm_adv_functions.md#storm-adv-functions) level names.

A private member must be used by a literal name, such as `$self.__seen`, so that a method which is given a name by its caller can not reach one. A private method belongs to the class which declares it, and may only be called, not taken as a value. A private value belongs to the class whose method sets it: each class in the chain of the instance has its own, so a class may neither read nor replace the private values of the class it extends or of the classes which extend it, even one of the same name.

This `Dedup` class reports whether a value has been seen before. How two values are judged to be the same, and the record of the values already seen, are internal details kept private so that they may change without affecting the code using the class. The count of skipped values is public:

```storm
class Dedup {

    method __storm_init() {
        $self.skipped = (0)
        $self.__seen = ({})
        return()
    }

    method isNew(valu) {
        $key = $self.__key($valu)
        if $self.__seen.$key {
            $self.skipped = ($self.skipped + 1)
            return((false))
        }
        $self.__seen.$key = (true)
        return((true))
    }

    method __key(valu) { return($valu.lower().strip()) }
}

$dedup = $Dedup()
for $name in (Vertex.link, "vertex.link ", woot.com, WOOT.COM) {
    if $dedup.isNew($name) { $lib.print(`new: {$name}`) }
}
$lib.print(`skipped {$dedup.skipped}`)
```

Output:

```stormdoc
new: Vertex.link
new: woot.com
skipped 2
```

Calling a private method from outside the class raises an error:

```storm
class Dedup {
    method __key(valu) { return($valu.lower().strip()) }
}

$dedup = $Dedup()
$dedup.__key(Vertex.link)
```

Output:

```stormdoc
ERROR: Cannot dereference private value [__key] on object of type Dedup.
```

<a id="storm-class-inherit"></a>

## Inheritance

A class may extend one other class using the `extends` keyword. The subclass inherits every method of the class it extends, and may override any of them.

Inside a method, `$super` resolves methods starting from the class being extended, which is how an overridden implementation is reached. `$super` may only be used to call a public method of that class, and may not be used to call one of its private methods.

This `CachingResolver` extends a `Resolver` which normalizes an FQDN. It overrides `resolve()` to remember each result, and calls `$super.resolve()` only for a name it has not seen:

```storm
class Resolver {
    method resolve(name) {
        $lib.print(`resolving {$name}`)
        return($lib.cast(inet:fqdn, $name))
    }
}

class CachingResolver extends Resolver {

    method __storm_init() {
        $self.__cache = ({})
        return()
    }

    method resolve(name) {
        if ($name not in $self.__cache) {
            $self.__cache.$name = $super.resolve($name)
        }
        return($self.__cache.$name)
    }
}

$resolver = $CachingResolver()
$lib.print($resolver.resolve(VERTEX.link))
$lib.print($resolver.resolve(VERTEX.link))
```

Output:

```stormdoc
resolving VERTEX.link
vertex.link
vertex.link
```

A call through `$self` resolves from the class which declared the calling method, not from the class of the instance. A base class method which calls `$self.describe()` runs the base class `describe()` even when a subclass overrides it. This applies only to a call written through `$self`: code which is handed the instance, including a function the method passes `$self` to, calls the subclass override as usual, so it is a rule of method dispatch rather than a security boundary:

```storm
class Base {
    method who() { return(base) }
    method ask() { return($self.who()) }
}

class Kid extends Base {
    method who() { return(kid) }
}

$kid = $Kid()
$lib.print(`{$kid.who()} {$kid.ask()}`)
```

Output:

```stormdoc
kid base
```

A subclass which declares no `__storm_init()` inherits the constructor of the class it extends. A subclass which **does** declare one must call `$super.__storm_init()` when the class it extends has a constructor, and construction fails if it does not, so that an instance is never used before every class in its chain has initialized its state. `Resolver` above has none, so `CachingResolver` does not call one.

Each `__storm_init()` method runs at most once for an instance. If a `__storm_init()` method raises an error, it may not be called again, and construction fails even when a subclass catches the error, so that a class may always refuse to be constructed. An instance whose construction fails may not be used, even if a `__storm_init()` method handed out `$self` before it failed.

`__storm_init()` and `__storm_fini()` are invoked by the runtime and may not be called directly. The one exception is an `__storm_init()` method calling `$super.__storm_init()` to run the constructor of the class it extends; any other call such as `$self.__storm_init()` or `$super.__storm_fini()` raises an error.

```storm
class Batcher {
    method __storm_fini() { return() }
    method close() { return($self.__storm_fini()) }
}

$batch = $Batcher()
$batch.close()
```

Output:

```stormdoc
...     method close() { return($self.__storm_fini()) } }  $bat...
                                 ^
Syntax Error: Batcher.__storm_fini() is invoked by the runtime and may not be called directly.
```

Cleanup behaves differently: every `__storm_fini()` method in the chain runs, starting with the most derived class, without the subclass needing to call `$super.__storm_fini()`. An error raised by one `__storm_fini()` method is reported as a Storm warning and does not prevent the others from running.

Here an `AuditedBatcher` adds its own cleanup to a `Batcher`. It fails, and the `Batcher` still sends its items:

```storm
class Batcher {

    method __storm_init() {
        $self.__items = ([])
        return()
    }

    method add(item) {
        $self.__items.append($item)
        return()
    }

    method __storm_fini() {
        $lib.print(`Batcher sent {$lib.len($self.__items)} items`)
        return()
    }
}

class AuditedBatcher extends Batcher {
    method __storm_fini() {
        $lib.raise(BadArg, "the audit record could not be written")
        return()
    }
}

$batch = $AuditedBatcher()
$batch.add(vertex.link)
$batch.fini()
```

Output:

```stormdoc
WARNING: AuditedBatcher.__storm_fini() failed for AuditedBatcher object: the audit record could not be written name=AuditedBatcher, err=BadArg
Batcher sent 1 items
```

<a id="storm-class-modules"></a>

## Classes in Storm Modules

A class declared at the top level of a Storm module is exported the same way a function is, so a module may hand out classes to its callers. This is how a power-up can give its users an object, such as a client for an external API, which does its work without exposing the secrets it relies on.

A class whose name begins with `__` is private to its module: it is not exported, but the module's own code may still use it. A module which hands out instances from a function, and keeps the class itself private, stops its callers from constructing the class with arguments of their choosing or declaring a subclass of it, which also rules out the subclass override described under [Privileges](#storm-class-privileges).

Given an `acme-intel` package with a privileged `acme.intel.client` module which reads an API key from the `acme-intel` [vault](storm_ref_cmd.md#storm-vault), whose secrets its users may not read:

```storm
function __getHeaders() {
    $vault = $lib.vault.byname(acme-intel)
    return(({"X-API-KEY": $vault.secrets.apikey}))
}

class Client {

    method lookup(fqdn as inet:fqdn) {

        $url = `https://acme.example.com/api/v1/fqdn/{$fqdn}`

        $resp = $lib.inet.http.get($url, headers=$__getHeaders())
        if ($resp.code != 200) {
            $lib.warn(`lookup of {$fqdn} returned HTTP code: {$resp.code}`)
            return()
        }

        return($resp.json())
    }
}
```

A user with the `acme.intel.user` permission may construct a `Client` and use it:

```storm
$client = $lib.import(acme.intel.client).Client()

$info = $client.lookup(VERTEX.link)
$lib.print(`{$info.fqdn} risk={$info.risk}`)
```

Output:

```stormdoc
vertex.link risk=low
```

> [!NOTE]
> A class instance cannot be converted into a primitive, so it may not be returned from a Storm query to an external caller the way a dictionary can. Instances are intended for use within Storm.

`$lib.utils.type()` of an instance reports a name which says where the class was declared, so it can never be mistaken for a built-in type. A class declared in a module is named by the module, like `acme.intel.client.Client`, and a class declared directly in a query is named `<query>.Client`. Naming a class after a built-in type, such as `str`, does not let its instances pass as that type.

<a id="storm-class-privileges"></a>

### Privileges

Like a function, a method runs with the privileges of the module or query which declared it, whoever calls it, and resolves variables in that module, so it may use the module's functions and variables. This includes `__storm_init()` and `__storm_fini()`: each `__storm_fini()` in the chain runs with the privileges of the code which declared it, whether the instance is finalized by a call to `fini()` or as the query finishes.

A class declared in a [privileged module](../devguides/power-ups.md#privileged-modules) therefore runs its methods with the module's privileges, and any code which may use the class may call its public methods. The methods of its classes are part of the code to review when auditing a privileged module, along with its functions. In the example above, `lookup()` runs with the module's privileges, and reads the API key only through the module's private `__getHeaders()` function, which keeps the code which reads the secret in one place.

Privileges follow the code which declared a method, not the object it is called on. A method inherited from a class in a privileged module keeps the module's privileges when it is called on an instance of a subclass, while a method which the subclass declares runs with the privileges of the code which declared the subclass. So when elevated code calls a method on an object it was handed, constructs a class it was handed, or calls `fini()` on one, the code it runs has the privileges of whoever declared it, not the elevated privileges. The same holds for a subclass override reached when an elevated base method passes `$self` to one of the module's functions. That override also receives whatever the base passes it, such as a secret. To keep private data away from a subclass, call the method through `$self`, which always runs the base's own method, or pass the module function the data rather than the instance.

Any code holding an instance may set its public values, so a method which runs elevated should not trust them. Keep the state such a method relies on private, such as the target of an edit made in `__storm_fini()`.

A private value is out of reach of other code, but the class which holds a secret may still give it away. The `Client` above avoids the common ways it could:

* The key is read from the vault each time it is used, and is never stored on the instance, so a key which is rotated or revoked in the vault takes effect on the next request.
* The key is passed directly to the request, and is never set in a variable of the method, where code the method runs, such as a query passed to `$lib.storm.eval()`, could read it. A caller could read one too: the nodes a method yields carry its variables in their paths, so code which uses `divert` on the method may read them from `$path.vars`.
* The endpoint the key is sent to is written in the class, and the argument used to build the request is normalized as an `inet:fqdn`, so a caller can not have the key sent to a server of its choosing.
* The key is never printed, included in a warning or error, or passed to a function given by the caller.

The key stays out of reach, but its use does not. `lookup()` runs with the privileges the module was imported with, so any code which is handed a `Client` may make requests with the key, even code running as a user who could not import the module. Hand an instance only to code which should be able to use it.
