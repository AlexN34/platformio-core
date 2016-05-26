# Copyright 2014-present Ivan Kravets <me@ikravets.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import click

from platformio import app, exception, util
from platformio.managers.platform import PlatformFactory, PlatformManager


@click.group(short_help="Platform Manager")
def cli():
    pass


def _print_platforms(platforms):
    for platform in platforms:
        click.echo("{name} ~ {title}".format(
            name=click.style(platform['name'], fg="cyan"),
            title=platform['title']))
        click.echo("=" * (3 + len(platform['name'] + platform['title'])))
        click.echo(platform['description'])
        click.echo()
        click.echo("Home: %s" %
                   "http://platformio.org/platforms/" + platform['name'])
        if platform['packages']:
            click.echo("Packages: %s" % ", ".join(platform['packages']))
        if "version" in platform:
            click.echo("Version: " + platform['version'])
        click.echo()


@cli.command("search", short_help="Search for development platforms")
@click.argument("query", required=False)
@click.option("--json-output", is_flag=True)
def platform_search(query, json_output):
    platforms = []
    for platform in util.get_api_result("/platforms"):
        if query == "all":
            query = ""

        search_data = json.dumps(platform)
        if query and query.lower() not in search_data.lower():
            continue

        # @TODO update API with NAME/TITLE
        platforms.append({
            "name": platform['type'],
            "title": platform['name'],
            "description": platform['description'],
            "packages": platform['packages']
        })

    if json_output:
        click.echo(json.dumps(platforms))
    else:
        _print_platforms(platforms)


@cli.command("install", short_help="Install new platforms")
@click.argument("platforms", nargs=-1, required=True)
@click.option("--with-package", multiple=True, metavar="<package>")
@click.option("--without-package", multiple=True, metavar="<package>")
@click.option("--skip-default-package", is_flag=True)
def platform_install(platforms, with_package, without_package,
                     skip_default_package):
    for platform in platforms:
        _platform = platform
        _version = None
        if "@" in platform:
            _platform, _version = platform.rsplit("@", 1)
        if PlatformManager().install(_platform, _version, with_package,
                                     without_package, skip_default_package):
            click.secho(
                "The platform '%s' has been successfully installed!\n"
                "The rest of packages will be installed automatically "
                "depending on your build environment." % platform,
                fg="green")


@cli.command("list", short_help="List installed platforms")
@click.option("--json-output", is_flag=True)
def platform_list(json_output):
    platforms = []
    for manifest in PlatformManager().get_installed():
        p = PlatformFactory.newPlatform(manifest['_manifest_path'])
        platforms.append({
            "name": p.get_name(),
            "title": p.get_title(),
            "description": p.get_description(),
            "version": p.get_version(),
            "packages": p.get_installed_packages().keys()
        })

    if json_output:
        click.echo(json.dumps(platforms))
    else:
        _print_platforms(platforms)


@cli.command("show", short_help="Show details about installed Platform")
@click.argument("platform")
@click.pass_context
def platform_show(ctx, platform):
    try:
        p = PlatformFactory.newPlatform(platform)
    except exception.UnknownPlatform:
        if (not app.get_setting("enable_prompts") or
                click.confirm("The platform '%s' has not been installed yet. "
                              "Would you like to install it now?" % platform)):
            ctx.invoke(platform_install, platforms=[platform])
        else:
            raise exception.PlatformNotInstalledYet(platform)

    click.echo("{name} ~ {title}".format(
        name=click.style(p.get_name(), fg="cyan"), title=p.get_title()))
    click.echo("=" * (3 + len(p.get_name() + p.get_title())))
    click.echo(p.get_manifest().get("description"))
    click.echo()
    click.echo("Version: %s" % p.get_version())
    if "homepage" in p.get_manifest():
        click.echo("Home: %s" % p.get_manifest().get("homepage"))
    if "license" in p.get_manifest():
        click.echo("License: %s" % p.get_manifest().get("license").get("type"))
    if "frameworks" in p.get_manifest():
        click.echo("Frameworks: %s" %
                   ", ".join(p.get_manifest().get("frameworks").keys()))

    if not p.get_packages():
        return

    installed_pkgs = p.get_installed_packages()
    for name, opts in p.get_packages().items():
        click.echo()
        click.echo("Package %s" % click.style(name, fg="yellow"))
        click.echo("-" * (8 + len(name)))
        if p.get_package_type(name):
            click.echo("Type: %s" % p.get_package_type(name))
        click.echo("Requirements: %s" % opts.get("version"))
        click.echo("Installed: %s" % (
            "Yes" if name in installed_pkgs else "No (optional)"))
        if name in installed_pkgs:
            for key, value in installed_pkgs[name].items():
                if key in ("url", "version", "description"):
                    click.echo("%s: %s" % (key.title(), value))


@cli.command("uninstall", short_help="Uninstall platforms")
@click.argument("platforms", nargs=-1, required=True)
def platform_uninstall(platforms):
    for platform in platforms:
        _platform = platform
        _version = None
        if "@" in platform:
            _platform, _version = platform.rsplit("@", 1)
        if PlatformManager().uninstall(_platform, _version):
            click.secho("The platform '%s' has been successfully "
                        "uninstalled!" % platform, fg="green")


@cli.command("update", short_help="Update installed Platforms")
@click.option("--only-packages", is_flag=True)
def platform_update(only_packages):
    for manifest in PlatformManager().get_installed():
        click.echo("Platform %s @ %s" % (
            click.style(manifest['name'], fg="cyan"), manifest['version']))
        click.echo("--------")
        if only_packages:
            status = PlatformFactory.newPlatform(
                manifest['name'], manifest['version']).update_packages()
            if status is None:
                click.secho("Packages are up-to-date", fg="green")
        else:
            PlatformManager().update(manifest['name'], manifest['version'])
        click.echo()
