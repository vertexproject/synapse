import synapse.exc as s_exc
import synapse.tests.utils as s_test

class ProjModelTest(s_test.SynTest):

    async def test_model_proj(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            lowuser = await core.auth.addUser('lowuser')

            asvisi = {'user': visi.iden}

            with self.raises(s_exc.AuthDeny):
                proj = await core.callStorm('return($lib.projects.add(foo))', opts=asvisi)
            await visi.addRule((True, ('project', 'add')), gateiden=core.view.iden)
            proj = await core.callStorm('return($lib.projects.add(foo))', opts=asvisi)
            self.nn(proj)

            opts = {'user': visi.iden, 'vars': {'proj': proj}}
            with self.raises(s_exc.AuthDeny):
                epic = await core.callStorm('return($lib.projects.get($proj).epics.add(bar))', opts=opts)
            await visi.addRule((True, ('project', 'epic', 'add')), gateiden=proj)
            epic = await core.callStorm('return($lib.projects.get($proj).epics.add(bar))', opts=opts)
            self.nn(epic)

            with self.raises(s_exc.AuthDeny):
                tick = await core.callStorm('return($lib.projects.get($proj).tickets.add(baz))', opts=opts)
            await visi.addRule((True, ('project', 'ticket', 'add')), gateiden=proj)
            tick = await core.callStorm('return($lib.projects.get($proj).tickets.add(baz))', opts=opts)
            self.nn(tick)

            with self.raises(s_exc.AuthDeny):
                sprint = await core.callStorm('return($lib.projects.get($proj).sprints.add(giterdone))', opts=opts)
            await visi.addRule((True, ('project', 'sprint', 'add')), gateiden=proj)
            sprint = await core.callStorm('return($lib.projects.get($proj).sprints.add(giterdone))', opts=opts)
            self.nn(sprint)

            opts = {'user': visi.iden, 'vars': {'proj': proj, 'epic': epic, 'tick': tick, 'sprint': sprint}}

            self.none(await core.callStorm('return($lib.projects.get(hehe))', opts=opts))
            self.none(await core.callStorm('return($lib.projects.get($proj).epics.get(haha))', opts=opts))
            self.none(await core.callStorm('return($lib.projects.get($proj).tickets.get(haha))', opts=opts))

            self.eq(proj, await core.callStorm('return($lib.projects.get($proj))', opts=opts))
            self.eq(epic, await core.callStorm('return($lib.projects.get($proj).epics.get($epic))', opts=opts))
            self.eq(tick, await core.callStorm('return($lib.projects.get($proj).tickets.get($tick))', opts=opts))

            self.eq('foo', await core.callStorm('return($lib.projects.get($proj).name)', opts=opts))
            self.eq('bar', await core.callStorm('return($lib.projects.get($proj).epics.get($epic).name)', opts=opts))
            self.eq('baz', await core.callStorm('return($lib.projects.get($proj).tickets.get($tick).name)', opts=opts))

            # test coverage for new storm primitive setitem default impl...
            with self.raises(s_exc.NoSuchName):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).newp = zoinks', opts=opts)

            # we created the ticket, so we can set these...
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).name = zoinks', opts=opts)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).desc = scoobie', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).assignee = visi', opts=opts)
            await visi.addRule((True, ('project', 'ticket', 'set', 'assignee')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).assignee = visi', opts=opts)
            # now as assignee visi should be able to update status
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).status = "in sprint"', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).sprint = giter', opts=opts)
            await visi.addRule((True, ('project', 'ticket', 'set', 'sprint')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).sprint = giter', opts=opts)

            aslow = dict(opts)
            aslow['user'] = lowuser.iden

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).name = zoinks', opts=aslow)
            await lowuser.addRule((True, ('project', 'ticket', 'set', 'name')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).name = zoinks', opts=aslow)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).epic = bar', opts=aslow)
            await lowuser.addRule((True, ('project', 'ticket', 'set', 'epic')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).epic = bar', opts=aslow)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).desc = scoobie', opts=aslow)
            await lowuser.addRule((True, ('project', 'ticket', 'set', 'desc')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).desc = scoobie', opts=aslow)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).status = done', opts=aslow)
            await lowuser.addRule((True, ('project', 'ticket', 'set', 'status')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).status = done', opts=aslow)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.get($tick).priority = highest', opts=opts)
            await visi.addRule((True, ('project', 'ticket', 'set', 'priority')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).tickets.get($tick).priority = highest', opts=opts)

            nodes = await core.nodes('proj:project')
            self.len(1, nodes)

            nodes = await core.nodes('proj:epic')
            self.len(1, nodes)
            self.eq(proj, nodes[0].get('project'))

            nodes = await core.nodes('proj:ticket')
            self.len(1, nodes)
            self.nn(nodes[0].get('creator'))
            self.nn(nodes[0].get('created'))
            self.nn(nodes[0].get('updated'))
            self.eq(70, nodes[0].get('status'))
            self.eq(50, nodes[0].get('priority'))
            self.eq('done', nodes[0].repr('status'))
            self.eq('highest', nodes[0].repr('priority'))
            self.eq(proj, nodes[0].get('project'))

            self.eq('foo', await core.callStorm('return($lib.projects.get($proj).name)', opts=opts))
            self.eq('bar', await core.callStorm('return($lib.projects.get($proj).epics.get($epic).name)', opts=opts))
            self.eq('zoinks', await core.callStorm('return($lib.projects.get($proj).tickets.get($tick).name)', opts=opts))
            self.eq('scoobie', await core.callStorm('return($lib.projects.get($proj).tickets.get($tick).desc)', opts=opts))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).epics.del($epic)', opts=opts)
            await visi.addRule((True, ('project', 'epic', 'del')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).epics.del($epic)', opts=opts)
            self.len(0, await core.nodes('proj:ticket:epic'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).sprints.del($sprint)', opts=opts)
            await visi.addRule((True, ('project', 'sprint', 'del')), gateiden=proj)
            await core.callStorm('$lib.projects.get($proj).sprints.del($sprint)', opts=opts)
            self.len(0, await core.nodes('proj:ticket:sprint'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.projects.get($proj).tickets.del($tick)', opts=aslow)
            # visi ( as creator ) can delete the ticket
            await core.callStorm('$lib.projects.get($proj).tickets.del($tick)', opts=opts)
