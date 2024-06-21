# Action Server UI

The Action Server provides a builtin UI which can help while developing actions.

## Disclaimer

In general, for deployment it's not expected that the Action Server
nor its UI are exposed directly, rather some kind of reverse proxy should be put
in front of it which would filter the traffic so that private parts of its REST API
are not exposed and https is done (while the Action Server does have support for
https, it lacks a way for clients to update the certificates without actually
restarting the server).

Note: when `action-server start --expose` is done it takes care of the details
noted above, but there's no real user or access management done.

## Purpose

The main purpose of the Action Server UI is for helping developers develop and
test actions or for internal users to query and analyze what was actually executed
in the Action Server.

![Action Server UI](./images/action-server-ui-initial.png)

Initial UI for the Action Server, shows actions loaded in the Action Server.

## Running an Action

To run an action, after clicking the action you want to run a panel will
open showing the data that needs to be filled to run the action.

![Action Server Run Action UI](./images/action-server-ui-run-action.png)

Example above shows a case where `OAuth2` is required for `Slack` and `Google`
to run the action along with a `count` parameter.

## Configuring OAuth2

In this case, a developer must create an application in the proper service
(say, `google` and `slack`), fill in the details in the `OAuth2 Settings`
and then do the proper `login` in the service in the `Run Action UI` to run the action.

The image below shows an example of configuration where `slack` and `google`
are configured.

![Action Server OAuth2 Settings UI](./images/action-server-ui-oauth2-settings.png)

Note: all the information entered (such as the OAuth2 data as well as secrets) is
encrypted and persisted in the browser local storage (so, if you change the URL at
which the Action Server is loaded or change from `http` to `https`, the data
will need to be reentered).

Also, while the information is encrypted, the key to decrypt the information is saved
in the filesystem so that it's available from the Action Server, so, if an attacker
is able to get into your computer he could have access to the key.
