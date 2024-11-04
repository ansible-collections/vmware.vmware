# Module Profiling and Performance

It might be useful to check module performance when developing.

## Timing Tasks

Ansible comes with a basic profiler that outputs how long each task takes. You can enable it by setting an environment variable:
```bash
export ANSIBLE_CALLBACKS_ENABLED=profile_tasks
```

## Profiling Modules

Python comes with a profiler that will show how long each method takes. Heres a very basic example:
```python
def main():
    # import the profiler and setup the context manager
    import cProfile
    import pstats
    with cProfile.Profile() as pr:
        argument_spec = VmwareRestClient.vmware_client_argument_spec()
        module = AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True,
        )

        # Execute your module as usual
        my_class = Foo(module)
        out = my_class.do()

        # save the profile results to a variable
        stats = pstats.Stats(pr)

    # sort by time and write the output to a file so you can view the results
    stats.sort_stats(pstats.SortKey.TIME)
    stats.dump_stats("/some/local/path/profile.prof")

    # exit module as usual
    module.exit_json(changed=False, out=out)
```

You can use a tool like `snakeviz` to view the profile results.
```bash
pip install snakeviz
snakviz /some/local/path/profile.prof
```
