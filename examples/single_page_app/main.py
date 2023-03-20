#!/usr/bin/env python3

from router import Router

from nicegui import ui

router = Router()


@router.add('/')
async def show_one():
    ui.label('Content One').classes('text-2xl')


@router.add('/two')
async def show_two():
    ui.label('Content Two').classes('text-2xl')


@router.add('/three')
async def show_three():
    ui.label('Content Three').classes('text-2xl')


@ui.page('/')  # normal index page (eg. the entry point of the app)
@ui.page('/{_:path}')  # all other pages will be handled by the router but must be registered to also show the SPA index page
async def main():
    # adding some navigation buttons to switch between the different pages
    with ui.row():
        ui.button('One', on_click=lambda: router.open(show_one)).classes('w-32')
        ui.button('Two', on_click=lambda: router.open(show_two)).classes('w-32')
        ui.button('Three', on_click=lambda: router.open(show_three)).classes('w-32')

    # this places the content which should be displayed
    router.frame().classes('w-full pt-8')

ui.run()
