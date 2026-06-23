# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

# Use the official runtime image to keep Python/Pemja/JVM ABI aligned.
FROM spg-registry.cn-hangzhou.cr.aliyuncs.com/spg/openspg-server:latest

ENV LANG=C.UTF-8
ENV PATH=/home/admin/miniconda3/bin:$PATH
ENV KAG_PROJECT_HOST_ADDR=http://127.0.0.1:8887
ENV KAG_PROJECT_ID=1
ENV OPENAI_API_KEY=your_api_key_here
ENV SILICONFLOW_API_KEY=your_api_key_here

COPY bridge/spg_server_bridge.py /tmp/spg_server_bridge.py
COPY target/kag-runtime.tar.gz /tmp/kag-runtime.tar.gz

RUN set -eux; \
    mkdir -p /home/admin/miniconda3/lib/python3.10/site-packages/bridge; \
    mkdir -p /tmp/kag-runtime; \
    tar -xzf /tmp/kag-runtime.tar.gz -C /tmp/kag-runtime; \
    cp -a /tmp/kag-runtime/kag /home/admin/miniconda3/lib/python3.10/site-packages/; \
    cp -a /tmp/kag-runtime/knext /home/admin/miniconda3/lib/python3.10/site-packages/; \
    mv /tmp/spg_server_bridge.py /home/admin/miniconda3/lib/python3.10/site-packages/bridge/spg_server_bridge.py; \
    : > /home/admin/miniconda3/lib/python3.10/site-packages/bridge/__init__.py; \
    rm -rf /tmp/kag-runtime /tmp/kag-runtime.tar.gz; \
    PYTHONPATH=/home/admin/miniconda3/lib/python3.10/site-packages /home/admin/miniconda3/bin/python -c "import kag,knext,pemja; from bridge.spg_server_bridge import SPGServerBridge; print('kag:', kag.__file__); print('knext:', knext.__file__); print('pemja:', pemja.__file__); print('bridge:', SPGServerBridge.__name__); print('runtime_ok')"

EXPOSE 8887

COPY target/arks-sofaboot-0.0.1-SNAPSHOT-executable.jar /
ENTRYPOINT ["java", "-jar", "arks-sofaboot-0.0.1-SNAPSHOT-executable.jar"]
