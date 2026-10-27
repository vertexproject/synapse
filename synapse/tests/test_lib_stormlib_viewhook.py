import synapse.exc as s_exc

import synapse.tests.utils as s_test

HOOKPOP = '''
    $retn = ()
    $queue = $lib.queue.gen(hooks)
    for ($offs, $item) in $queue.gets(wait=(false)) { $retn.append($item) }
    if $retn { $queue.cull($offs) }
    return($retn)
'''

class ViewHookTest(s_test.SynTest):

    async def test_stormlib_viewhook(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            self.eq([], await core.callStorm('return($lib.view.hook.list())'))

            # $lib.view functions still work alongside the nested lib
            self.len(1, await core.callStorm('return($lib.view.list())'))

            iden = await core.callStorm('return($lib.view.hook.add(woot, created, ${ $lib.print(hi) }).iden)')
            hdef = await core.getViewHook(iden)
            self.eq(iden, hdef.get('iden'))
            self.eq('woot', hdef.get('name'))
            self.eq('created', hdef.get('type'))
            self.eq(' $lib.print(hi) ', hdef.get('storm'))
            self.true(hdef.get('enabled'))
            self.eq(core.auth.rootuser.iden, hdef.get('creator'))
            self.eq(hdef.get('created'), hdef.get('updated'))

            opts = {'vars': {'iden': iden}}
            q = '''
                $hook = $lib.view.hook.get($iden)
                return(($hook.iden, $hook.name, $hook.type, $hook.storm, $hook.enabled,
                        $hook.creator, $hook.created, $hook.updated))
            '''
            self.eq((iden, 'woot', 'created', ' $lib.print(hi) ', True, core.auth.rootuser.iden,
                     hdef.get('created'), hdef.get('updated')), await core.callStorm(q, opts=opts))

            msgs = await core.stormlist('$lib.print($lib.view.hook.get($iden))', opts=opts)
            self.stormIsInPrint(f'view:hook: woot ({iden})', msgs)

            iden2 = await core.callStorm('return($lib.view.hook.add(nope, deleted, "", enabled=(false)).iden)')
            hdef2 = await core.getViewHook(iden2)
            self.false(hdef2.get('enabled'))
            self.eq('deleted', hdef2.get('type'))

            hooks = await core.callStorm('''
                $retn = ()
                for $hook in $lib.view.hook.list() { $retn.append($hook.iden) }
                return($retn)
            ''')
            self.eq([iden, iden2], hooks)

            # get and list are allowed in a readonly runtime
            ropts = {'vars': {'iden': iden}, 'readonly': True}
            self.eq('woot', await core.callStorm('return($lib.view.hook.get($iden).name)', opts=ropts))
            self.len(2, await core.callStorm('return($lib.view.hook.list())', opts=ropts))

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('$lib.view.hook.get($iden).name = newp', opts=ropts)

            # stors update the hook and the local value
            q = '''
                $hook = $lib.view.hook.get($iden)
                $hook.name = hehe
                $hook.type = merging
                $hook.storm = ${ $lib.print(haha) }
                $hook.enabled = (false)
                return(($hook.name, $hook.type, $hook.storm, $hook.enabled, $hook.updated))
            '''
            name, htype, storm, enabled, updated = await core.callStorm(q, opts=opts)
            self.eq(('hehe', 'merging', ' $lib.print(haha) ', False), (name, htype, storm, enabled))
            self.ge(updated, hdef.get('updated'))

            hdef = await core.getViewHook(iden)
            self.eq('hehe', hdef.get('name'))
            self.eq('merging', hdef.get('type'))
            self.eq(' $lib.print(haha) ', hdef.get('storm'))
            self.false(hdef.get('enabled'))
            self.eq(updated, hdef.get('updated'))

            # validation errors
            with self.raises(s_exc.SchemaViolation):
                await core.callStorm('$lib.view.hook.add(newp, newp, "")')

            with self.raises(s_exc.SchemaViolation):
                await core.callStorm('$lib.view.hook.add("", created, "")')

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('$lib.view.hook.add(newp, created, "inet:fqdn=")')

            with self.raises(s_exc.SchemaViolation):
                await core.callStorm('$lib.view.hook.get($iden).type = newp', opts=opts)

            with self.raises(s_exc.SchemaViolation):
                await core.callStorm('$lib.view.hook.get($iden).name = ""', opts=opts)

            with self.raises(s_exc.BadSyntax):
                await core.callStorm('$lib.view.hook.get($iden).storm = "inet:fqdn="', opts=opts)

            with self.raises(s_exc.NoSuchName):
                await core.callStorm('$lib.view.hook.get($iden).creator = newp', opts=opts)

            self.eq('hehe', (await core.getViewHook(iden)).get('name'))
            self.len(2, await core.getViewHooks())

            with self.raises(s_exc.NoSuchIden):
                await core.callStorm('$lib.view.hook.get(newp)')

            with self.raises(s_exc.NoSuchIden):
                await core.callStorm('$lib.view.hook.del(newp)')

            # every function and stor requires global admin
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.hook.add(newp, created, "")', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.hook.get($iden)', opts={'user': visi.iden, 'vars': {'iden': iden}})

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.hook.list()', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.hook.del($iden)', opts={'user': visi.iden, 'vars': {'iden': iden}})

            vopts = {'user': visi.iden, 'vars': {'iden': iden}}
            for name, valu in (('name', 'newp'), ('type', 'created'), ('storm', '$lib.print(newp)'), ('enabled', True)):
                await visi.setAdmin(True)
                q = f'''
                    $hook = $lib.view.hook.get($iden)
                    $lib.auth.users.byname(visi).setAdmin((false))
                    $hook.{name} = $valu
                '''
                vopts['vars']['valu'] = valu
                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(q, opts=vopts)

            self.false(visi.isAdmin())
            hdef = await core.getViewHook(iden)
            self.eq(('hehe', 'merging', ' $lib.print(haha) ', False),
                    (hdef.get('name'), hdef.get('type'), hdef.get('storm'), hdef.get('enabled')))

            # a global admin may manage hooks and is the creator of the ones they add
            await visi.setAdmin(True)
            q = '$hook = $lib.view.hook.add(visi, created, "") return(($hook.iden, $hook.creator))'
            iden3, creator = await core.callStorm(q, opts=asvisi)
            self.eq(visi.iden, creator)
            self.eq(visi.iden, (await core.getViewHook(iden3)).get('creator'))

            await core.callStorm('$lib.view.hook.del($iden)', opts={'user': visi.iden, 'vars': {'iden': iden}})
            await core.callStorm('$lib.view.hook.del($iden)', opts={'vars': {'iden': iden2}})
            await core.callStorm('$lib.view.hook.del($iden)', opts={'vars': {'iden': iden3}})
            self.eq([], await core.callStorm('return($lib.view.hook.list())'))

            with self.raises(s_exc.NoSuchIden):
                await core.getViewHook(iden)

            # hooks added from storm run as root in the view for each lifecycle event
            hookput = '$lib.queue.gen(hooks).put(($name, $lib.auth.users.get().name, $lib.view.get().iden))'

            q = '''
                $lib.view.hook.add(created, created, `$name=created {$hookput}`)
                $lib.view.hook.add(merging, merging, `$name=merging {$hookput}`)
                $lib.view.hook.add(deleted, deleted, `$name=deleted {$hookput}`)
            '''
            await core.callStorm(q, opts={'user': visi.iden, 'vars': {'hookput': hookput}})

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            self.eq([('created', 'root', forkiden)], await core.callStorm(HOOKPOP))

            await core.callStorm('$lib.view.del($iden)', opts={'vars': {'iden': forkiden}})
            self.none(core.getView(forkiden))
            self.eq([('deleted', 'root', forkiden)], await core.callStorm(HOOKPOP))

            forkiden = await core.callStorm('return($lib.view.get().fork().iden)')
            self.eq([('created', 'root', forkiden)], await core.callStorm(HOOKPOP))

            await core.nodes('[ test:str=hookmerge ]', opts={'view': forkiden})
            await core.callStorm('$lib.view.get().merge()', opts={'view': forkiden})
            self.len(1, await core.nodes('test:str=hookmerge'))
            self.eq([('merging', 'root', forkiden)], await core.callStorm(HOOKPOP))
